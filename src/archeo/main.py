from fastapi import FastAPI, HTTPException, UploadFile, File
from .core.engine import ArchimateEngine
from .models.store import store, ArchiMateModel, ArchiMateVersion
import uuid

app = FastAPI(title="ArchiMate Enterprise Manager", version="1.0.0")

@app.post("/models/import")
async def import_model(name: str, version: ArchiMateVersion):
    # This is a placeholder for the XML parser (app/core/importer.py)
    model_id = str(uuid.uuid4())
    new_model = ArchiMateModel(model_id=model_id, name=name, version=version)
    store.add_model(new_model)
    return {"model_id": model_id, "status": "imported"}

@app.get("/models/{model_id}/search")
async def search_elements(model_id: str, q: str = None):
    try:
        return ArchimateEngine.navigate_elements(model_id, q)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/models/migrate/{model_id}")
async def migrate_model(model_id: str, target_version: ArchiMateVersion):
    try:
        return ArchimateEngine.migrate_version(model_id, target_version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/models/compare")
async def compare(a: str, b: str):
    try:
        return ArchimateEngine.compare_models(a, b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
