from pydantic import BaseModel, Field

from app.models.base import BaseElement

# Motivation Layer
class Assessment(BaseElement): pass
class Constraint(BaseElement): pass
class Driver(BaseElement): pass
class Goal(BaseElement): pass
class Meaning(BaseElement): pass
class Outcome(BaseElement): pass
class Principle(BaseElement): pass
class Requirement(BaseElement): pass
class Stakeholder(BaseElement): pass
class Value(BaseElement): pass

# Strategy Layer
class Capability(BaseElement): pass
class CourseOfActions(BaseElement): pass
class Resource(BaseElement): pass
class ValueStream(BaseElement): pass

# Business Layer
class BusinessActor(BaseElement): pass
class BusinessCollaboration(BaseElement): pass
class BusinessEvent(BaseElement): pass
class BusinessFunction(BaseElement): pass
class BusinessInteration(BaseElement): pass
class BusinessInterface(BaseElement): pass
class BusinessObject(BaseElement): pass
class BusinessProcess(BaseElement): pass
class BusinessService(BaseElement): pass
class BusinessRole(BaseElement): pass
class Contact(BaseElement): pass
class Product(BaseElement): pass
class Representation(BaseElement): pass

# Application Layer
class ApplicationCollaboration(BaseElement): pass
class ApplicationComponent(BaseElement): pass
class ApplicationEvent(BaseElement): pass
class ApplicationFunction(BaseElement): pass
class ApplicationInteraction(BaseElement): pass
class ApplicationInterface(BaseElement): pass
class ApplicationProcess(BaseElement): pass
class ApplicationService(BaseElement): pass
class DataObject(BaseElement): pass

# Technology Layer
class Artifact(BaseElement): pass
class CommunicationNetwork(BaseElement): pass
class Device(BaseElement): pass
class DistributionNetwork(BaseElement): pass
class Equipment(BaseElement): pass
class Facility(BaseElement): pass
class Material(BaseElement): pass
class Node(BaseElement): pass
class Path(BaseElement): pass
class SystemSoftware(BaseElement): pass
class TechnologyCollaboration(BaseElement): pass
class TechnologyEvent(BaseElement): pass
class TechnologyFunction(BaseElement): pass
class TechnologyInteraction(BaseElement): pass
class TechnologyInterface(BaseElement): pass
class TechnologProcess(BaseElement): pass
class TechnologyService(BaseElement): pass

# Implementation & Migration Layer
class Delivrable(BaseElement): pass
class Gap(BaseElement): pass
class ImplementationEvent(BaseElement): pass
class Plateau(BaseElement): pass
class WorkPackage(BaseElement): pass

# Other Layer
class Grouping(BaseElement): pass
class Junction(BaseElement): pass
class Location(BaseElement): pass
