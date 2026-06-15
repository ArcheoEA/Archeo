import logging

from neo4j import GraphDatabase
from typing import List, Optional

from app.core.store import BaseStore, ArchimateModel
from app.models.base import BaseElement, Relationship

logger = logging.getLogger(__name__)

class Neo4jStore(BaseStore):
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_model(self, model: ArchimateModel):
        with self.driver.session() as session:
            # 1. Create Model Node
            session.run("CREATE (m:Model {id: $id, name: $name, version: $version})", 
                        id=model.model_id, name=model.name, version=model.version.value)

            # 2. Create Elements as Nodes linked to Model
            for elem_id, elem in model.elements.items():
                # Use the class name (e.g., 'BusinessProcess') as the Neo4j Label
                label = elem.__class__.__name__
                session.run(
                    f"CREATE (e:{label} {{id: $id, name: $name}}) "
                    f"WITH e MATCH (m:Model {{id: $mid}}) CREATE (m)-[:CONTAINS]->(e)",
                    id=elem_id, name=elem.name, mid=model.model_id
                )

            # 3. Create Relationships as Edges
            for rel in model.relationships:
                rel_type = rel.type.value.upper()
                session.run(
                    f"MATCH (a {{id: $source}}), (b {{id: $target}}) "
                    f"CREATE (a)-[:{rel_type}]->(b)",
                    source=rel.source, target=rel.target
                )
        logger.info(f"Model {model.model_id} persisted to Neo4j.")

    def get_model(self, model_id: str) -> Optional[ArchimateModel]:
        # Note: Reconstructing a full Pydantic model from Neo4j is heavy.
        # In a real app, we would use Neo4j for queries and only fetch metadata here.
        return None # Implementation omitted for brevity

    def list_models(self) -> List[str]:
        with self.driver.session() as session:
            result = session.run("MATCH (m:Model) RETURN m.id as id")
            return [record["id"] for record in result]

    def search_elements(self, model_id: str, query: str) -> List[BaseElement]:
        with self.driver.session() as session:
            # Cypher query to find elements belonging to a model matching the name
            cypher = """
            MATCH (m:Model {id: $mid})-[:CONTAINS]->(e)
            WHERE e.name CONTAINS $query
            RETURN e.id as id, e.name as name, labels(e)[0] as type
            """
            result = session.run(cypher, mid=model_id, query=query)
            # Mapping back to BaseElements (Simplified)
            return [BaseElement(id=r["id"], name=r["name"]) for r in result]
