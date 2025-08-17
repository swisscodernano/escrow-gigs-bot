import asyncio
import logging
import os
from decimal import Decimal

from sqlalchemy.orm import Session
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.config import settings
from app.db_utils import db_session_decorator
from app.lang_command import cmd_lang
from app.models import Dispute, Gig, Order, User
from app.payment.ledger import new_deposit_address
from app.payment.tron_stub import validate_deposit_tx
from app.translator import get_translation


async def ensure_user(tg_user, db: Session) -> User:
    u = db.query(User).filter(User.tg_id == str(tg_user.id)).first()
    if not u:
        u = User(tg_id=str(tg_user.id), username=tg_user.username or "")
        db.add(u)
        db.flush()
        db.refresh(u)
    else:
        if u.username != (tg_user.username or ""):
            u.username = tg_user.username or ""
    return u


@db_session_decorator
async def cmd_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    keyboard = [
        [
            InlineKeyboardButton(_("New Gig (USDT)"), callback_data="new_gig_usdt"),
            InlineKeyboardButton(_("New Gig (BTC)"), callback_data="new_gig_btc"),
        ],
        [InlineKeyboardButton(_("Listings"), callback_data="listings")],
        [
            InlineKeyboardButton(_("My Gigs"), callback_data="my_gigs"),
            InlineKeyboardButton(_("My Orders"), callback_data="my_orders"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        _("👋 Welcome to the *Gigs Escrow Bot*\n\nPlease choose an option:"),
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


@db_session_decorator
async def button(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    data = query.data
    if data.startswith("view_gig_"):
        gig_id = int(data.split("_")[2])
        await view_gig_details(update, context, gig_id=gig_id)
    elif data.startswith("toggle_gig_"):
        gig_id = int(data.split("_")[2])
        await toggle_gig_status(update, context, gig_id=gig_id)
    elif data == "listings":
        await cmd_listings(update, context)
    elif data == "my_gigs":
        await cmd_mygigs(update, context)
    elif data.startswith("manage_order_"):
        await manage_order(update, context)
    elif data == "my_orders":
        await cmd_orders(update, context)


@db_session_decorator
async def cmd_help(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    await update.message.reply_text(
        _(
            "Available commands:\n"
            "/start - Start the bot\n"
            "/newgig <Title> | <price_usd> | <description> - Create a new gig in USDT\n"
            "/newgigbtc <Title> | <price_btc> | <description> - Create a new gig in BTC\n"
            "/listings - Show active gigs\n"
            "/mygigs - Show your gigs\n"
            "/buy <id> - Buy a gig\n"
            "/confirm_tx <id> <txid> - Confirm a transaction\n"
            "/release <id> - Release funds to the seller\n"
            "/dispute <id> <reason> - Open a dispute\n"
            "/orders - Show your orders\n"
            "/lang <en|it> - Set your language"
        )
    )


# States for /newgig conversation
TITLE, PRICE, DESCRIPTION = range(3)
# States for /newgigbtc conversation
BTC_TITLE, BTC_PRICE, BTC_DESCRIPTION = range(3, 6)
# State for /buy conversation
CONFIRM_PURCHASE = 6
# State for /confirm_tx conversation
RECEIVE_TXID = 7
# State for /release conversation
CONFIRM_RELEASE = 8
# State for /dispute conversation
RECEIVE_REASON = 9
# States for review conversation
GIVE_RATING, GIVE_COMMENT = range(10, 12)


@db_session_decorator
async def new_gig_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Starts the conversation and asks for a title."""
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    await message.reply_text(
        _("Let's create a new gig! What is the title?"),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(_("Cancel"), callback_data="cancel")]]
        ),
    )
    return TITLE


@db_session_decorator
async def receive_title(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Stores the title and asks for the price."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    context.user_data["title"] = update.message.text
    await update.message.reply_text(
        _("Great! Now, what is the price in USD?"),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(_("Cancel"), callback_data="cancel")]]
        ),
    )
    return PRICE


@db_session_decorator
async def receive_price(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Stores the price and asks for the description."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    try:
        price = Decimal(update.message.text)
        context.user_data["price"] = price
        await update.message.reply_text(
            _("Got it. Finally, please provide a short description."),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(_("Cancel"), callback_data="cancel")]]
            ),
        )
        return DESCRIPTION
    except Exception as e:
        logging.error(f"Error converting price: {e}")
        await update.message.reply_text(
            _("The price must be a number. Please try again."),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(_("Cancel"), callback_data="cancel")]]
            ),
        )
        return PRICE


@db_session_decorator
async def receive_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Stores the description, creates the gig, and ends the conversation."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    context.user_data["description"] = update.message.text

    title = context.user_data["title"]
    price = context.user_data["price"]
    description = context.user_data["description"]

    seller = db.query(User).filter(User.tg_id == str(user.tg_id)).first()
    g = Gig(
        seller_id=seller.id,
        title=title,
        description=description,
        price_usd=price,
        currency=settings.PRIMARY_ASSET,
    )
    db.add(g)
    db.flush()
    db.refresh(g)

    await update.message.reply_text(
        _("✅ Gig #{gig_id} created: *{title}* — ${price} ({currency})").format(
            gig_id=g.id, title=title, price=price, currency=settings.PRIMARY_ASSET
        ),
        parse_mode="Markdown",
    )

    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def start_review(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Starts the review conversation."""
    query = update.callback_query
    await query.answer()

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    try:
        _, order_id, reviewee_id = query.data.split("_")
        context.user_data["review_order_id"] = int(order_id)
        context.user_data["review_reviewee_id"] = int(reviewee_id)
        context.user_data["review_reviewer_id"] = user.id
    except ValueError:
        await query.message.reply_text(
            _("Something went wrong. Could not start review process.")
        )
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton("⭐", callback_data="rating_1"),
            InlineKeyboardButton("⭐⭐", callback_data="rating_2"),
            InlineKeyboardButton("⭐⭐⭐", callback_data="rating_3"),
            InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rating_4"),
            InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rating_5"),
        ],
        [InlineKeyboardButton(_("Cancel"), callback_data="cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(
        _("Please rate your experience with the other user (1-5 stars):"),
        reply_markup=reply_markup,
    )

    return GIVE_RATING


@db_session_decorator
async def receive_rating(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Receives the rating and asks for a comment."""
    query = update.callback_query
    await query.answer()

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    try:
        rating = int(query.data.split("_")[1])
        context.user_data["review_rating"] = rating
    except (ValueError, IndexError):
        await query.message.reply_text(_("Invalid rating. Please try again."))
        return GIVE_RATING

    keyboard = [
        [InlineKeyboardButton(_("Skip Comment"), callback_data="skip_comment")],
        [InlineKeyboardButton(_("Cancel"), callback_data="cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(
        _("Thank you for the rating! Would you like to add a public comment? (optional)"),
        reply_markup=reply_markup,
    )

    return GIVE_COMMENT


@db_session_decorator
async def receive_comment(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Receives the comment, saves the feedback, and ends the conversation."""
    from app.models import Feedback, Order

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    comment = update.message.text

    order_id = context.user_data.get("review_order_id")
    reviewer_id = context.user_data.get("review_reviewer_id")
    reviewee_id = context.user_data.get("review_reviewee_id")
    rating = context.user_data.get("review_rating")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        await update.message.reply_text(_("Error: Original order not found."))
        context.user_data.clear()
        return ConversationHandler.END

    review_type = "buyer_review" if reviewer_id == order.buyer_id else "seller_review"

    feedback = Feedback(
        order_id=order_id,
        reviewer_id=reviewer_id,
        reviewee_id=reviewee_id,
        score=rating,
        comment=comment,
        review_type=review_type,
    )
    db.add(feedback)

    await update.message.reply_text(_("✅ Thank you for your feedback!"))

    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def skip_comment(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Saves feedback without a comment and ends the conversation."""
    from app.models import Feedback, Order

    query = update.callback_query
    await query.answer()

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    order_id = context.user_data.get("review_order_id")
    reviewer_id = context.user_data.get("review_reviewer_id")
    reviewee_id = context.user_data.get("review_reviewee_id")
    rating = context.user_data.get("review_rating")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        await query.message.edit_text(_("Error: Original order not found."))
        context.user_data.clear()
        return ConversationHandler.END

    review_type = "buyer_review" if reviewer_id == order.buyer_id else "seller_review"

    feedback = Feedback(
        order_id=order_id,
        reviewer_id=reviewer_id,
        reviewee_id=reviewee_id,
        score=rating,
        comment=None,
        review_type=review_type,
    )
    db.add(feedback)

    await query.message.edit_text(_("✅ Thank you for your feedback!"))

    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Cancels and ends the conversation."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message

    await message.reply_text(_("Operation cancelled."))
    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def new_gig_btc_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Starts the BTC gig conversation and asks for a title."""
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    await message.reply_text(
        _("Let's create a new BTC gig! What is the title?"),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(_("Cancel"), callback_data="cancel")]]
        ),
    )
    return BTC_TITLE


@db_session_decorator
async def receive_btc_title(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Stores the title and asks for the price."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    context.user_data["title"] = update.message.text
    await update.message.reply_text(
        _("Great! Now, what is the price in BTC?"),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(_("Cancel"), callback_data="cancel")]]
        ),
    )
    return BTC_PRICE


@db_session_decorator
async def receive_btc_price(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Stores the price and asks for the description."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    try:
        price = Decimal(update.message.text)
        context.user_data["price_btc"] = price
        await update.message.reply_text(
            _("Got it. Finally, please provide a short description."),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(_("Cancel"), callback_data="cancel")]]
            ),
        )
        return BTC_DESCRIPTION
    except Exception as e:
        logging.error(f"Error converting btc price: {e}")
        await update.message.reply_text(
            _("The price must be a number (e.g. 0.001). Please try again."),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(_("Cancel"), callback_data="cancel")]]
            ),
        )
        return BTC_PRICE


@db_session_decorator
async def receive_btc_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Stores the description, creates the gig, and ends the conversation."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    context.user_data["description"] = update.message.text

    title = context.user_data["title"]
    price_btc = context.user_data["price_btc"]
    description = context.user_data["description"]

    seller = db.query(User).filter(User.tg_id == str(user.tg_id)).first()
    g = Gig(
        seller_id=seller.id,
        title=title,
        description=description,
        price_usd=price_btc,  # Using price_usd column for BTC amount
        currency="BTC-ONCHAIN",
    )
    db.add(g)
    db.flush()
    db.refresh(g)

    await update.message.reply_text(
        _("✅ BTC Gig #{gig_id} created: *{title}* — {price_btc} BTC").format(
            gig_id=g.id, title=title, price_btc=price_btc
        ),
        parse_mode="Markdown",
    )

    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def cmd_listings(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    gigs = (
        db.query(Gig).filter(Gig.active == True).order_by(Gig.id.desc()).limit(10).all()
    )

    message = update.callback_query.message if update.callback_query else update.message

    if not gigs:
        await message.reply_text(_("No gigs at the moment. /newgig"))
        return

    text = _("📋 *Available Gigs:*\n\n")
    keyboard = []
    for g in gigs:
        text += f"#{g.id} — *{g.title}* — ${g.price_usd} — {g.currency}\n"
        keyboard.append(
            [InlineKeyboardButton(f"Buy Gig #{g.id}", callback_data=f"buy_{g.id}")]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)

    # If called from a button, edit the message. Otherwise, send a new one.
    if update.callback_query:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@db_session_decorator
async def cmd_mygigs(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
):
    u = await ensure_user(update.effective_user, db)
    _ = get_translation(u)
    seller = db.query(User).filter(User.tg_id == str(u.tg_id)).first()
    gigs = (
        db.query(Gig).filter(Gig.seller_id == seller.id).order_by(Gig.id.desc()).all()
    )

    message = update.callback_query.message if update.callback_query else update.message

    if not gigs:
        await message.reply_text(
            _("You have no gigs. To create one, use the /start menu.")
        )
        return

    text = _("🧾 *Your Gigs:*\n\n")
    keyboard = []
    for g in gigs:
        status = _("Active") if g.active else _("Inactive")
        text += f"#{g.id} — *{g.title}* — ${g.price_usd} ({g.currency}) — Status: {status}\n"
        keyboard.append(
            [
                InlineKeyboardButton(
                    _("View Details"), callback_data=f"view_gig_{g.id}"
                ),
                InlineKeyboardButton(
                    _("Deactivate") if g.active else _("Activate"),
                    callback_data=f"toggle_gig_{g.id}",
                ),
            ]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@db_session_decorator
async def view_gig_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    gig_id: int,
    db: Session = None,
):
    query = update.callback_query
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    gig = db.query(Gig).filter(Gig.id == gig_id, Gig.seller_id == user.id).first()

    if not gig:
        await query.message.reply_text(_("Gig not found or you are not the owner."))
        return

    text = f"""
*Gig Details for #{gig.id}*
*Title:* {gig.title}
*Price:* ${gig.price_usd} {gig.currency}
*Description:* {gig.description}
*Status:* {'Active' if gig.active else 'Inactive'}
"""
    keyboard = [[InlineKeyboardButton(_("Back to My Gigs"), callback_data="my_gigs")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(
        _(text), reply_markup=reply_markup, parse_mode="Markdown"
    )


@db_session_decorator
async def toggle_gig_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    gig_id: int,
    db: Session = None,
):
    query = update.callback_query
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    gig = db.query(Gig).filter(Gig.id == gig_id, Gig.seller_id == user.id).first()
    if not gig:
        await query.message.reply_text(_("Gig not found or you are not the owner."))
        return

    gig.active = not gig.active
    db.add(gig)

    # After toggling, show the updated list of gigs
    await cmd_mygigs(update, context)


@db_session_decorator
async def buy_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Starts the buy conversation, shows gig details and asks for confirmation."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    gig_id = None
    query = update.callback_query
    if query and query.data.startswith("buy_"):
        await query.answer()
        gig_id = int(query.data.split("_")[1])
        message = query.message
    elif update.message and context.args:
        try:
            gig_id = int(context.args[0])
            message = update.message
        except (IndexError, ValueError):
            await update.message.reply_text(
                _("Please provide a valid Gig ID. Usage: /buy <gig_id>")
            )
            return ConversationHandler.END
    else:
        # This could happen if /buy is called without args
        await update.message.reply_text(
            _("Please provide a Gig ID. Usage: /buy <gig_id>")
        )
        return ConversationHandler.END

    g = db.query(Gig).filter(Gig.id == gig_id, Gig.active == True).first()
    if not g:
        await message.reply_text(_("Gig not found or inactive."))
        return ConversationHandler.END

    # Store gig_id for the next step
    context.user_data["buy_gig_id"] = gig_id

    part1 = _("You are about to purchase the following gig:")
    part2 = _("Price: ${price} ({currency})").format(
        price=g.price_usd, currency=g.currency
    )
    part3 = _("Please confirm your purchase.")
    text = part1 + "\n\n*" + g.title + "*\n" + part2 + "\n\n" + part3

    keyboard = [
        [
            InlineKeyboardButton(
                _("Confirm Purchase"), callback_data=f"confirm_purchase"
            ),
            InlineKeyboardButton(_("Cancel"), callback_data="cancel_purchase"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return CONFIRM_PURCHASE


@db_session_decorator
async def confirm_purchase(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Creates the order and provides deposit details."""
    query = update.callback_query
    await query.answer()

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    gig_id = context.user_data.get("buy_gig_id")
    if not gig_id:
        await query.message.edit_text(_("Something went wrong. Please try again."))
        return ConversationHandler.END

    g = db.query(Gig).filter(Gig.id == gig_id, Gig.active == True).first()
    if not g:
        await query.message.edit_text(_("Gig not found or is no longer active."))
        return ConversationHandler.END

    buyer_obj = db.query(User).filter(User.tg_id == str(user.tg_id)).first()

    # Check if user is trying to buy their own gig
    if g.seller_id == buyer_obj.id:
        await query.message.edit_text(_("You cannot buy your own gig."))
        context.user_data.clear()
        return ConversationHandler.END

    o = Order(
        gig_id=g.id,
        buyer_id=buyer_obj.id,
        seller_id=g.seller_id,
        status="AWAIT_DEPOSIT",
        expected_amount=g.price_usd,
        escrow_fee_pct=8.00,
    )
    db.add(o)
    db.flush()
    db.refresh(o)

    dep = new_deposit_address(o.id, g.currency)
    o.deposit_address = dep.address
    db.add(o)

    text = _(
        "🛡️ Order #{oid} created successfully!\n\n"
        "Please deposit *{amt}* {asset} to the following address:\n"
        "`{addr}`\n\n"
        "After making the payment, use the /confirm_tx command:\n"
        "`/confirm_tx {oid} <your_transaction_id>`"
    ).format(oid=o.id, amt=g.price_usd, asset=g.currency, addr=o.deposit_address)

    await query.message.edit_text(text, parse_mode="Markdown")

    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def cancel_purchase(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Cancels the purchase conversation."""
    query = update.callback_query
    await query.answer()
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    await query.message.edit_text(_("Purchase cancelled."))
    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def confirm_tx_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Starts the confirm_tx conversation and asks for the transaction ID."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    order_id = None
    query = update.callback_query
    if query and query.data.startswith("confirm_tx_"):
        await query.answer()
        order_id = int(query.data.split("_")[2])
        message = query.message
    elif update.message and context.args:
        try:
            order_id = int(context.args[0])
            message = update.message
        except (IndexError, ValueError):
            await update.message.reply_text(
                _("Please provide a valid Order ID. Usage: /confirm_tx <order_id>")
            )
            return ConversationHandler.END
    else:
        await update.message.reply_text(
            _("Please provide an Order ID. Usage: /confirm_tx <order_id>")
        )
        return ConversationHandler.END

    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        await message.reply_text(_("Order not found."))
        return ConversationHandler.END

    # Check if the user is the buyer
    buyer = db.query(User).filter(User.tg_id == str(update.effective_user.id)).first()
    if o.buyer_id != buyer.id:
        await message.reply_text(_("You are not the buyer for this order."))
        return ConversationHandler.END

    if o.status != "AWAIT_DEPOSIT":
        await message.reply_text(_("This order is not awaiting deposit."))
        return ConversationHandler.END

    context.user_data["confirm_order_id"] = order_id

    text = _(
        "You are confirming payment for Order #{order_id}. Please reply with your transaction ID (txid)."
    ).format(order_id=order_id)
    keyboard = [[InlineKeyboardButton(_("Cancel"), callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return RECEIVE_TXID


@db_session_decorator
async def receive_txid(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Receives the txid and confirms the transaction."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    order_id = context.user_data.get("confirm_order_id")
    if not order_id:
        await update.message.reply_text(
            _(
                "Something went wrong. Please try again starting with /confirm_tx <order_id>."
            )
        )
        return ConversationHandler.END

    txid = update.message.text.strip()

    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        await update.message.reply_text(_("Order not found."))
        context.user_data.clear()
        return ConversationHandler.END

    ok = False
    if o.gig.currency.startswith("USDT-TRON"):
        ok = await validate_deposit_tx(txid, Decimal(o.expected_amount))
    elif o.gig.currency.startswith("BTC-ONCHAIN"):
        from app.payment import btc_onchain

        ok = await btc_onchain.validate_deposit(
            o.deposit_address, Decimal(o.expected_amount)
        )

    if not ok:
        await update.message.reply_text(
            _(
                "⚠️ Invalid deposit. The transaction ID might be wrong, or the deposited amount is incorrect. Please try again or contact support."
            )
        )
        # We can let them try again
        return RECEIVE_TXID

    o.txid = txid
    o.status = "FUNDS_HELD"
    db.add(o)

    await update.message.reply_text(
        _(
            "✅ Deposit confirmed for Order #{oid}. The funds are now held in escrow. The seller has been notified. You can release the funds using /release {oid} once you are satisfied."
        ).format(oid=order_id)
    )

    # Notify seller
    try:
        seller_tg_id = o.seller.tg_id
        await context.bot.send_message(
            chat_id=seller_tg_id,
            text=_(
                "🎉 The buyer has confirmed the payment for Order #{oid}. The funds are now in escrow."
            ).format(oid=order_id),
        )
    except Exception as e:
        logging.error(
            f"Failed to send notification to seller for order {order_id}: {e}"
        )

    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def release_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Starts the release conversation and asks for confirmation."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    order_id = None
    query = update.callback_query
    if query and query.data.startswith("release_"):
        await query.answer()
        order_id = int(query.data.split("_")[1])  # assuming release_{order_id}
        message = query.message
    elif update.message and context.args:
        try:
            order_id = int(context.args[0])
            message = update.message
        except (IndexError, ValueError):
            await update.message.reply_text(
                _("Please provide a valid Order ID. Usage: /release <order_id>")
            )
            return ConversationHandler.END
    else:
        await update.message.reply_text(
            _("Please provide an Order ID. Usage: /release <order_id>")
        )
        return ConversationHandler.END

    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        await message.reply_text(_("Order not found."))
        return ConversationHandler.END

    # Check if the user is the buyer
    buyer = db.query(User).filter(User.tg_id == str(update.effective_user.id)).first()
    if o.buyer_id != buyer.id:
        await message.reply_text(_("You are not the buyer for this order."))
        return ConversationHandler.END

    if o.status != "FUNDS_HELD":
        await message.reply_text(
            _("This order's funds are not currently held in escrow.")
        )
        return ConversationHandler.END

    context.user_data["release_order_id"] = order_id

    text = _(
        "You are about to release the funds for Order #{order_id}. This action is irreversible. The funds will be sent to the seller. Please confirm."
    ).format(order_id=order_id)
    keyboard = [
        [
            InlineKeyboardButton(
                _("Confirm & Release Funds"), callback_data="confirm_release"
            ),
            InlineKeyboardButton(_("Cancel"), callback_data="cancel_release"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return CONFIRM_RELEASE


@db_session_decorator
async def execute_release(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Releases the funds and ends the conversation."""
    query = update.callback_query
    await query.answer()

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    order_id = context.user_data.get("release_order_id")
    if not order_id:
        await query.message.edit_text(_("Something went wrong. Please try again."))
        return ConversationHandler.END

    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        await query.message.edit_text(_("Order not found."))
        context.user_data.clear()
        return ConversationHandler.END

    # Double check ownership and status
    buyer = db.query(User).filter(User.tg_id == str(update.effective_user.id)).first()
    if o.buyer_id != buyer.id:
        await query.message.edit_text(_("You are not the buyer for this order."))
        context.user_data.clear()
        return ConversationHandler.END
    if o.status != "FUNDS_HELD":
        await query.message.edit_text(
            _("This order's funds are not currently held in escrow.")
        )
        context.user_data.clear()
        return ConversationHandler.END

    o.status = "RELEASED"
    db.add(o)

    await query.message.edit_text(
        _(
            "🔓 Funds for Order #{oid} have been released to the seller. Thank you for using our service!"
        ).format(oid=order_id)
    )

    # Notify seller and prompt for review
    try:
        seller_tg_id = o.seller.tg_id
        review_keyboard_seller = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        _("Leave a Review"),
                        callback_data=f"start_review_{o.id}_{o.buyer_id}",
                    )
                ]
            ]
        )
        await context.bot.send_message(
            chat_id=seller_tg_id,
            text=_(
                "✅ The buyer has released the funds for Order #{oid}. The order is now complete. Please leave a review for the buyer."
            ).format(oid=order_id),
            reply_markup=review_keyboard_seller,
        )
    except Exception as e:
        logging.error(
            f"Failed to send release notification to seller for order {order_id}: {e}"
        )

    # Prompt buyer to review seller
    try:
        buyer_tg_id = o.buyer.tg_id
        review_keyboard_buyer = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        _("Leave a Review"),
                        callback_data=f"start_review_{o.id}_{o.seller_id}",
                    )
                ]
            ]
        )
        await context.bot.send_message(
            chat_id=buyer_tg_id,
            text=_(
                "Your order #{oid} is complete. Please leave a review for the seller."
            ).format(oid=order_id),
            reply_markup=review_keyboard_buyer,
        )
    except Exception as e:
        logging.error(
            f"Failed to send review prompt to buyer for order {order_id}: {e}"
        )

    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def cancel_release(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Cancels the release conversation."""
    query = update.callback_query
    await query.answer()
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    await query.message.edit_text(_("Release cancelled."))
    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def dispute_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Starts the dispute conversation and asks for a reason."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    order_id = None
    query = update.callback_query
    if query and query.data.startswith("dispute_"):
        await query.answer()
        order_id = int(query.data.split("_")[1])  # assuming dispute_{order_id}
        message = query.message
    elif update.message and context.args:
        try:
            order_id = int(context.args[0])
            message = update.message
        except (IndexError, ValueError):
            await update.message.reply_text(
                _("Please provide a valid Order ID. Usage: /dispute <order_id>")
            )
            return ConversationHandler.END
    else:
        await update.message.reply_text(
            _("Please provide an Order ID. Usage: /dispute <order_id>")
        )
        return ConversationHandler.END

    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        await message.reply_text(_("Order not found."))
        return ConversationHandler.END

    # Check if the user is part of the order
    user_obj = (
        db.query(User).filter(User.tg_id == str(update.effective_user.id)).first()
    )
    if o.buyer_id != user_obj.id and o.seller_id != user_obj.id:
        await message.reply_text(_("You are not part of this order."))
        return ConversationHandler.END

    if o.status != "FUNDS_HELD":
        await message.reply_text(
            _("A dispute can only be opened for orders with funds in escrow.")
        )
        return ConversationHandler.END

    context.user_data["dispute_order_id"] = order_id

    text = _(
        "You are opening a dispute for Order #{order_id}. Please describe the issue clearly."
    ).format(order_id=order_id)
    keyboard = [[InlineKeyboardButton(_("Cancel"), callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await message.edit_text(text, reply_markup=reply_markup)
    else:
        await message.reply_text(text, reply_markup=reply_markup)

    return RECEIVE_REASON


@db_session_decorator
async def receive_dispute_reason(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
) -> int:
    """Receives the reason and opens the dispute."""
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    order_id = context.user_data.get("dispute_order_id")
    if not order_id:
        await update.message.reply_text(_("Something went wrong. Please try again."))
        return ConversationHandler.END

    reason = update.message.text.strip()

    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        await update.message.reply_text(_("Order not found."))
        context.user_data.clear()
        return ConversationHandler.END

    user_obj = db.query(User).filter(User.tg_id == str(user.tg_id)).first()

    # Double check user is part of order and status
    if o.buyer_id != user_obj.id and o.seller_id != user_obj.id:
        await update.message.reply_text(_("You are not part of this order."))
        context.user_data.clear()
        return ConversationHandler.END
    if o.status != "FUNDS_HELD":
        await update.message.reply_text(
            _("A dispute can only be opened for orders with funds in escrow.")
        )
        context.user_data.clear()
        return ConversationHandler.END

    d = Dispute(order_id=o.id, opened_by=user_obj.id, reason=reason, status="OPEN")
    db.add(d)

    # Optionally, update order status
    o.status = "DISPUTED"
    db.add(o)

    await update.message.reply_text(
        _(
            "🧑‍⚖️ Dispute opened for Order #{oid}. An administrator will review it shortly."
        ).format(oid=order_id)
    )

    if settings.ADMIN_USER_ID:
        try:
            await context.bot.send_message(
                chat_id=settings.ADMIN_USER_ID,
                text=_(
                    "⚖️ New dispute for order {oid} by user {user_id}.\nReason: {reason}"
                ).format(oid=order_id, user_id=user_obj.id, reason=reason),
            )
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END


@db_session_decorator
async def manage_order(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
):
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split("_")[2])

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    user_obj = db.query(User).filter(User.tg_id == str(user.tg_id)).first()

    o = db.query(Order).filter(Order.id == order_id).first()
    if not o or (o.buyer_id != user_obj.id and o.seller_id != user_obj.id):
        await query.message.edit_text(_("Order not found or you are not part of it."))
        return

    is_buyer = o.buyer_id == user_obj.id
    role = _("Buyer") if is_buyer else _("Seller")

    text = _(
        "🛍️ *Managing Order #{oid}*\n\n"
        "Gig: *{gig_title}*\n"
        "Price: ${price} ({currency})\n"
        "Status: `{status}`\n"
        "Your Role: {user_role}\n\n"
        "Choose an action:"
    ).format(
        oid=o.id,
        gig_title=o.gig.title,
        price=o.expected_amount,
        currency=o.gig.currency,
        status=o.status,
        user_role=role,
    )

    keyboard_rows = []
    if is_buyer:
        if o.status == "AWAIT_DEPOSIT":
            keyboard_rows.append(
                [
                    InlineKeyboardButton(
                        _("Confirm Payment"), callback_data=f"confirm_tx_{o.id}"
                    )
                ]
            )
        elif o.status == "FUNDS_HELD":
            keyboard_rows.append(
                [
                    InlineKeyboardButton(
                        _("Release Funds"), callback_data=f"release_{o.id}"
                    ),
                    InlineKeyboardButton(
                        _("Open Dispute"), callback_data=f"dispute_{o.id}"
                    ),
                ]
            )
    else:  # is_seller
        if o.status == "FUNDS_HELD":
            keyboard_rows.append(
                [
                    InlineKeyboardButton(
                        _("Open Dispute"), callback_data=f"dispute_{o.id}"
                    )
                ]
            )

    keyboard_rows.append(
        [InlineKeyboardButton(_("⬅️ Back to Orders"), callback_data="my_orders")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard_rows)

    await query.message.edit_text(
        text, reply_markup=reply_markup, parse_mode="Markdown"
    )


@db_session_decorator
async def cmd_orders(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    user_obj = db.query(User).filter(User.tg_id == str(user.tg_id)).first()
    orders = (
        db.query(Order)
        .filter((Order.buyer_id == user_obj.id) | (Order.seller_id == user_obj.id))
        .order_by(Order.id.desc())
        .limit(10)
        .all()
    )

    message = update.callback_query.message if update.callback_query else update.message

    if not orders:
        text = _("You have no orders.")
        if update.callback_query:
            await message.edit_text(text)
        else:
            await message.reply_text(text)
        return

    text = _("📦 *Your Orders:*\n\n")
    keyboard = []
    for o in orders:
        text += _("#{oid} - *{gig_title}* - Status: `{status}`\n").format(
            oid=o.id, gig_title=o.gig.title, status=o.status
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    _("Manage Order #{oid}").format(oid=o.id),
                    callback_data=f"manage_order_{o.id}",
                )
            ]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@db_session_decorator
async def cmd_profile(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
):
    """Displays the user's profile and stats."""
    from sqlalchemy import func
    from app.models import Feedback

    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)

    # Calculate rating stats
    rating_stats = (
        db.query(func.avg(Feedback.score), func.count(Feedback.id))
        .filter(Feedback.reviewee_id == user.id)
        .first()
    )

    avg_rating = rating_stats[0] or 0
    num_reviews = rating_stats[1] or 0

    # Calculate completed orders
    completed_orders = (
        db.query(Order)
        .filter(
            ((Order.buyer_id == user.id) | (Order.seller_id == user.id))
            & (Order.status == "RELEASED")
        )
        .count()
    )

    # Format the rating string
    rating_str = f"{Decimal(avg_rating):.1f} ⭐" if avg_rating else _("Not rated yet")

    text = _(
        "👤 *Your Profile*\n\n"
        "**Username:** @{username}\n"
        "**Rating:** {rating} ({reviews} reviews)\n"
        "**Completed Orders:** {orders}"
    ).format(
        username=user.username,
        rating=rating_str,
        reviews=num_reviews,
        orders=completed_orders,
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def run_bot_background():
    log = logging.getLogger(__name__)
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        log.warning("TELEGRAM_TOKEN not set: bot NOT started.")
        return

    log.info("Building bot application...")
    app = ApplicationBuilder().token(token).build()

    # Define commands and their handlers directly
    commands = {
        "start": ("👋 Start the bot", cmd_start),
        "help": ("❓ Show help", cmd_help),
        "mygigs": ("🧾 See your gigs", cmd_mygigs),
        "profile": ("👤 Show your profile", cmd_profile),
        "lang": ("🌐 Change language", cmd_lang),
    }

    new_gig_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("newgig", new_gig_start),
            CallbackQueryHandler(new_gig_start, pattern="^new_gig_usdt$"),
        ],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price)],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
    )
    app.add_handler(new_gig_conv_handler)

    new_gig_btc_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("newgigbtc", new_gig_btc_start),
            CallbackQueryHandler(new_gig_btc_start, pattern="^new_gig_btc$"),
        ],
        states={
            BTC_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_btc_title)
            ],
            BTC_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_btc_price)
            ],
            BTC_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_btc_description)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
    )
    app.add_handler(new_gig_btc_conv_handler)

    buy_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("buy", buy_start),
            CallbackQueryHandler(buy_start, pattern=r"^buy_\d+$"),
        ],
        states={
            CONFIRM_PURCHASE: [
                CallbackQueryHandler(confirm_purchase, pattern="^confirm_purchase$")
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_purchase, pattern="^cancel_purchase$")],
    )
    app.add_handler(buy_conv_handler)

    confirm_tx_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("confirm_tx", confirm_tx_start),
            CallbackQueryHandler(confirm_tx_start, pattern=r"^confirm_tx_\d+$"),
        ],
        states={
            RECEIVE_TXID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_txid)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
    )
    app.add_handler(confirm_tx_conv_handler)

    dispute_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("dispute", dispute_start),
            CallbackQueryHandler(dispute_start, pattern=r"^dispute_\d+$"),
        ],
        states={
            RECEIVE_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_dispute_reason)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
    )
    app.add_handler(dispute_conv_handler)

    review_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_review, pattern=r"^start_review_\d+_\d+$")
        ],
        states={
            GIVE_RATING: [
                CallbackQueryHandler(receive_rating, pattern=r"^rating_[1-5]$"),
            ],
            GIVE_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment),
                CallbackQueryHandler(skip_comment, pattern="^skip_comment$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
    )
    app.add_handler(review_conv_handler)

    bot_commands = [BotCommand(cmd, desc) for cmd, (desc, _) in commands.items()]
    for cmd, (_, handler) in commands.items():
        app.add_handler(CommandHandler(cmd, handler))

    app.add_handler(CallbackQueryHandler(button))

    log.info(f"Added {len(commands)} command handlers.")

    await app.initialize()
    await app.start()

    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.bot.set_my_commands(bot_commands)
        log.info("Bot commands set.")

        await app.updater.start_polling()
        log.info("Telegram bot is running and polling for updates.")

        # Keep the bot running
        while True:
            await asyncio.sleep(3600)

    except asyncio.CancelledError:
        log.info("Bot operation was cancelled.")
    except Exception as e:
        log.critical(
            f"A critical error occurred in the bot's main loop: {e}", exc_info=True
        )
    finally:
        log.info("Shutting down bot...")
        try:
            if app.updater and app.updater.is_running:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()
            log.info("Telegram bot stopped cleanly.")
        except Exception as e:
            log.error(f"Error during bot shutdown: {e}", exc_info=True)
