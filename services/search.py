from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session


def search_gigs(db: Session, query: str, limit: int = 10) -> List[Dict]:
    query = query.strip()
    if not query:
        return []
    dialect = db.bind.dialect.name
    if dialect == "sqlite":
        match = " OR ".join(query.split())
        sql = text(
            """
            SELECT g.id, g.title, g.price_usd,
                   snippet(gigs_fts, 0, '', '', '...', 10) AS snippet,
                   bm25(gigs_fts) AS rank
            FROM gigs_fts
            JOIN gigs g ON g.id = gigs_fts.rowid
            WHERE gigs_fts MATCH :q AND g.active = 1
            ORDER BY rank
            LIMIT :limit
            """
        )
        params = {"q": match, "limit": limit}
    else:
        sql = text(
            """
            SELECT g.id, g.title, g.price_usd,
                   substring(g.description from 1 for 200) AS snippet,
                   ts_rank(to_tsvector('english', g.title || ' ' || g.description),
                           plainto_tsquery('english', :q)) AS rank
            FROM gigs g
            WHERE to_tsvector('english', g.title || ' ' || g.description) @@ plainto_tsquery('english', :q)
              AND g.active = TRUE
            ORDER BY rank DESC
            LIMIT :limit
            """
        )
        params = {"q": query, "limit": limit}
    rows = db.execute(sql, params).mappings().all()
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "price_usd": float(r["price_usd"]),
            "excerpt": r["snippet"],
        }
        for r in rows
    ]
