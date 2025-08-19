from fastapi import APIRouter, Depends, Form, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db_core import get_db
from app.models import Dispute, Order

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_session(session: str | None = Cookie(None)):
    if not session or session != "admin_logged_in":
        return None
    return session

@router.get("/admin/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})

@router.post("/admin/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "password": # In a real app, use a secure password hash
        response = RedirectResponse(url="/admin/dashboard", status_code=303)
        response.set_cookie(key="session", value="admin_logged_in") # Placeholder for session management
        return response
    return RedirectResponse(url="/admin/login", status_code=303)

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), session: str = Depends(get_session)):
    if not session:
        return RedirectResponse(url="/admin/login", status_code=303)
    disputes = db.query(Dispute).filter(Dispute.status == "OPEN").all()
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "disputes": disputes})

@router.get("/admin/disputes/{dispute_id}", response_class=HTMLResponse)
async def dispute_details(request: Request, dispute_id: int, db: Session = Depends(get_db), session: str = Depends(get_session)):
    if not session:
        return RedirectResponse(url="/admin/login", status_code=303)
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    order = db.query(Order).filter(Order.id == dispute.order_id).first()
    return templates.TemplateResponse("admin/dispute_detail.html", {"request": request, "dispute": dispute, "order": order})

@router.post("/admin/disputes/{dispute_id}/resolve/buyer")
async def resolve_for_buyer(dispute_id: int, db: Session = Depends(get_db), session: str = Depends(get_session)):
    if not session:
        return RedirectResponse(url="/admin/login", status_code=303)
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    dispute.status = "CLOSED_BUYER_FAVOR"
    db.add(dispute)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@router.post("/admin/disputes/{dispute_id}/resolve/seller")
async def resolve_for_seller(dispute_id: int, db: Session = Depends(get_db), session: str = Depends(get_session)):
    if not session:
        return RedirectResponse(url="/admin/login", status_code=303)
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    dispute.status = "CLOSED_SELLER_FAVOR"
    db.add(dispute)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)
