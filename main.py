import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Dog

app = FastAPI(title="Pedigree Organizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DogCreate(BaseModel):
    name: str
    op_id: Optional[int] = None
    sex: Optional[str] = None
    color: Optional[str] = None
    birth_date: Optional[str] = None
    sire_id: Optional[str] = None
    dam_id: Optional[str] = None
    tags: List[str] = []
    source_url: Optional[str] = None
    notes: Optional[str] = None


def to_public(doc: Dict[str, Any]):
    if not doc:
        return doc
    d = {**doc}
    if "_id" in d and isinstance(d["_id"], ObjectId):
        d["id"] = str(d.pop("_id"))
    return d

@app.get("/")
def read_root():
    return {"message": "Pedigree Organizer Backend is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

@app.post("/dogs")
def create_dog(payload: DogCreate):
    data = payload.model_dump()
    dog = Dog(**data)  # validate
    new_id = create_document("dog", dog)
    return {"id": new_id}

@app.get("/dogs")
def list_dogs(q: Optional[str] = Query(None, description="Search by name"), limit: int = 50):
    filt: Dict[str, Any] = {}
    if q:
        # simple regex search by name
        filt = {"name": {"$regex": q, "$options": "i"}}
    docs = get_documents("dog", filt, limit)
    return [to_public(d) for d in docs]

@app.get("/dogs/{dog_id}")
def get_dog(dog_id: str):
    try:
        doc = db["dog"].find_one({"_id": ObjectId(dog_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    if not doc:
        raise HTTPException(status_code=404, detail="Dog not found")
    return to_public(doc)

@app.get("/pedigree/{dog_id}")
def get_pedigree(dog_id: str, depth: int = 3):
    """Return a small pedigree tree up to given depth (sire/dam ancestors)."""
    try:
        root = db["dog"].find_one({"_id": ObjectId(dog_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    if not root:
        raise HTTPException(status_code=404, detail="Dog not found")

    def fetch(node: Dict[str, Any], level: int):
        if level >= depth:
            return to_public(node)
        result = to_public(node)
        for rel in ["sire_id", "dam_id"]:
            nid = node.get(rel)
            if nid:
                try:
                    target = db["dog"].find_one({"_id": ObjectId(nid)})
                    result[rel[:-3]] = fetch(target, level + 1) if target else None
                except Exception:
                    result[rel[:-3]] = None
            else:
                result[rel[:-3]] = None
        return result

    return fetch(root, 0)

@app.post("/import")
def import_from_op(url: str):
    """
    Minimal importer: accepts a dog page URL from apbt.online-pedigrees.com and stores
    the root dog with reference to the source. Detailed scraping is not implemented
    due to site TOS; this creates a placeholder using the title.
    """
    import requests
    from bs4 import BeautifulSoup

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch: {e}")

    # Best-effort parse of page title for dog name
    name = None
    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string if soup.title else None
        if title:
            name = title.split("- ")[0].strip()
    except Exception:
        pass

    if not name:
        name = "Imported Dog"

    dog = Dog(
        name=name,
        source_url=url,
        notes="Imported from APBT Online Pedigrees (metadata only)",
    )
    new_id = create_document("dog", dog)
    return {"id": new_id, "name": name}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
