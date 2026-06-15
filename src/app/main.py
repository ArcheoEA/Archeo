import uuid

from fastapi import FastAPI, HTTPException, UploadFile, File, Form

from app.core.engine import ArchimateEngine
from app.core.importer import ArchimateImporter
from app.models.store import store, ArchiMateModel, ArchiMateVersion

app = FastAPI(title="ArchiMate Enterprise Manager", version="1.0.0")

@app.post("/models/import")
async def import_model(
    name: str = Form(...), 
    version: ArchiMateVersion = Form(...), 
    file: UploadFile = File(...)
):
    """
    Endpoint to upload an ArchiMate XML file and load it into in-memory storage.
    """
    try:
        # Read file content
        content = await file.read()
        model_id = str(uuid.uuid4())
        
        # Use the Importer to create the Pydantic model
        imported_model = ArchimateImporter.import_from_xml(content, model_id)
        
        # Override version if explicitly requested via API
        imported_model.version = version
        
        # Store in memory
        store.add_model(imported_model)
        
        return {
            "model_id": model_id, 
            "name": imported_model.name, 
            "elements_count": len(imported_model.elements),
            "status": "imported"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

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
