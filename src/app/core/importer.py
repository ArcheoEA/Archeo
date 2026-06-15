import logging
from lxml import etree
from typing import Dict, Type
from app.models.base import BaseElement, Relationship, ArchiMateVersion
from app.models.layers import *
from .store import ArchimateModel

# Setup logger
logger = logging.getLogger(__name__)

class ArchimateImporter:
    """
    Service responsible for parsing Open Group ArchiMate Exchange File Format XML 
    and converting it into Pydantic Model instances.
    """

    # Mapping of XML 'type' attributes to Pydantic Classes
    # This ensures strict formalism as requested.
    TYPE_MAP: Dict[str, Type[BaseElement]] = {
        # Motivation Layer
        "Assessment": Assessment,
        "Constraint": Constraint,
        "Driver": Driver,
        "Goal": Goal,
        "Meaning": Meaning,
        "Outcome": Outcome,
        "Principle": Principle,
        "Requirement": Requirement,
        "Stakeholder": Stakeholder,
        "Value": Value,
        
        # Strategy Layer
        "Capability": Capability,
        "CourseOfActions": CourseOfActions,
        "Resource": Resource,
        "ValueStream": ValueStream,
        
        # Business Layer
        "BusinessActor": BusinessActor,
        "BusinessCollaboration": BusinessCollaboration,
        "BusinessEvent": BusinessEvent,
        "BusinessFunction": BusinessFunction,
        "BusinessInteration": BusinessInteration,
        "BusinessInterface": BusinessInterface,
        "BusinessObject": BusinessObject,
        "BusinessProcess": BusinessProcess,
        "BusinessService": BusinessService,
        "BusinessRole": BusinessRole,
        "Contact": Contact,
        "Product": Product,
        "Representation": Representation,
        
        # Application Layer
        "ApplicationCollaboration": ApplicationCollaboration,
        "ApplicationComponent": ApplicationComponent,
        "ApplicationEvent": ApplicationEvent,
        "ApplicationFunction": ApplicationFunction,
        "ApplicationInteraction": ApplicationInteraction,
        "ApplicationInterface": ApplicationInterface,
        "ApplicationProcess": ApplicationProcess,
        "ApplicationService": ApplicationService,
        "DataObject": DataObject,
        
        # Technology Layer
        "Artifact": Artifact,
        "CommunicationNetwork": CommunicationNetwork,
        "Device": Device,
        "DistributionNetwork": DistributionNetwork,
        "Equipment": Equipment,
        "Facility": Facility,
        "Material": Material,
        "Node": Node,
        "Path": Path,
        "SystemSoftware": SystemSoftware,
        "TechnologyCollaboration": TechnologyCollaboration,
        "TechnologyEvent": TechnologyEvent,
        "TechnologyFunction": TechnologyFunction,
        "TechnologyInteraction": TechnologyInteraction,
        "TechnologyInterface": TechnologyInterface,
        "TechnologProcess": TechnologProcess,
        "TechnologyService": TechnologyService,

        # Implementation & Migration Layer
        "Delivrable": Delivrable,
        "Gap": Gap,
        "ImplementationEvent": ImplementationEvent,
        "Plateau": Plateau,
        "WorkPackage": WorkPackage,

        # Other Layer
        "Grouping": Grouping,
        "Junction": Junction,
        "Location": Location
    }

    @classmethod
    def import_from_xml(cls, xml_content: bytes, model_id: str) -> ArchimateModel:
        """
        Parses XML bytes and returns an ArchimateModel object.
        """
        try:
            # Parse XML with lxml
            root = etree.fromstring(xml_content)
            
            # ArchiMate XMLs usually use namespaces. We handle them dynamically.
            ns = {k if k is not None else 'default': v for k, v in root.nsmap.items()}
            
            # 1. Extract Model Metadata
            # The root is usually <exchange>, the model is inside <model>
            model_node = root.find(".//default:model", ns) if 'default' in ns else root.find(".//model")
            
            if model_node is None:
                raise ValueError("Invalid ArchiMate XML: <model> element not found.")

            model_name = model_node.get("name", "Unknown Model")
            
            # Determine version based on namespace or attribute (defaulting to 3.2 for this impl)
            version = ArchiMateVersion.V3_2 
            
            # Initialize the Pydantic Model container
            arch_model = ArchimateModel(
                model_id=model_id,
                name=model_name,
                version=version
            )

            # 2. Parse Elements
            elements_node = model_node.find(".//default:elements", ns) if 'default' in ns else model_node.find(".//elements")
            if elements_node is not None:
                for elem in elements_node.xpath(".//default:element", namespaces=ns) if 'default' in ns else elements_node.xpath(".//element"):
                    cls._parse_element(elem, arch_model)

            # 3. Parse Relationships
            rel_node = model_node.find(".//default:relationships", ns) if 'default' in ns else model_node.find(".//relationships")
            if rel_node is not None:
                for rel in rel_node.xpath(".//default:relationship", namespaces=ns) if 'default' in ns else rel_node.xpath(".//relationship"):
                    cls._parse_relationship(rel, arch_model)

            logger.info(f"Successfully imported model '{model_name}' with {len(arch_model.elements)} elements.")
            return arch_model

        except etree.XMLSyntaxError as e:
            logger.error(f"XML Syntax Error: {str(e)}")
            raise ValueError(f"Malformed XML file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during import: {str(e)}")
            raise e

    @classmethod
    def _parse_element(cls, node, arch_model: ArchimateModel):
        """Maps an XML element node to a Pydantic class based on the type attribute."""
        elem_id = node.get("identifier")
        elem_type = node.get("type")
        elem_name = node.get("name", "Unnamed Element")

        if not elem_id or not elem_type:
            logger.warning("Skipping element missing identifier or type.")
            return

        # Look up the specific Pydantic class from our map
        element_class = cls.TYPE_MAP.get(elem_type, BaseElement)
        
        # Instantiate the class (Pydantic handles the validation)
        element_instance = element_class(
            id=elem_id,
            name=elem_name
        )
        
        arch_model.elements[elem_id] = element_instance

    @classmethod
    def _parse_relationship(cls, node, arch_model: ArchimateModel):
        """Maps an XML relationship node to the Relationship Pydantic class."""
        rel_id = node.get("identifier")
        rel_type = node.get("type")
        source = node.get("source")
        target = node.get("target")

        if not all([rel_id, rel_type, source, target]):
            logger.warning("Skipping relationship missing critical attributes.")
            return

        # Relationship types in XML should match the RelationshipType Enum strings
        try:
            relationship_instance = Relationship(
                id=rel_id,
                type=rel_type,
                source=source,
                target=target
            )
            arch_model.relationships.append(relationship_instance)
        except ValueError as e:
            logger.error(f"Unsupported relationship type '{rel_type}': {e}")
