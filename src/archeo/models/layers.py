from pydantic import BaseModel, Field

from models.base import BaseElement

# Motivation Layer
class Stakeholder(BaseElement): pass
class Driver(BaseElement): pass
class Goal(BaseElement): pass
class Requirement(BaseElement): pass

# Strategy Layer
class Resource(BaseElement): pass
class Capability(BaseElement): pass

# Business Layer
class BusinessActor(BaseElement): pass
class BusinessProcess(BaseElement): pass
class BusinessService(BaseElement): pass
class BusinessObject(BaseElement): pass

# Application Layer
class ApplicationComponent(BaseElement): pass
class ApplicationService(BaseModel): pass
class DataObject(BaseElement): pass

# Technology Layer
class Node(BaseElement): pass
class SystemSoftware(BaseElement): pass
class Artifact(BaseElement): pass
