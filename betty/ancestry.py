from enum import Enum
from functools import total_ordering
from os.path import splitext, basename
from typing import Dict, Optional, List, Iterable, Tuple

from geopy import Point


class EventHandlingSet:
    def __init__(self, addition_handler=None, removal_handler=None):
        self._values = set()
        self._addition_handler = addition_handler
        self._removal_handler = removal_handler

    def add(self, *values):
        for value in values:
            self._add_one(value)

    def _add_one(self, value):
        if value in self._values:
            return
        self._values.add(value)
        if self._addition_handler is not None:
            self._addition_handler(value)

    def remove(self, value):
        if value not in self._values:
            return
        self._values.remove(value)
        if self._removal_handler is not None:
            self._removal_handler(value)

    def replace(self, values: Iterable):
        for value in set(self._values):
            self.remove(value)
        for value in values:
            self.add(value)

    def __iter__(self):
        return self._values.__iter__()

    def __len__(self):
        return len(self._values)


@total_ordering
class Date:
    def __init__(self, year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None):
        self._year = year
        self._month = month
        self._day = day

    @property
    def year(self) -> Optional[int]:
        return self._year

    @property
    def month(self) -> Optional[int]:
        return self._month

    @property
    def day(self) -> Optional[int]:
        return self._day

    @property
    def complete(self) -> bool:
        return self._year is not None and self._month is not None and self._day is not None

    @property
    def parts(self) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        return self._year, self._month, self._day

    def __eq__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        return self.parts == other.parts

    def __lt__(self, other):
        if not isinstance(other, Date):
            return NotImplemented
        if None in self.parts or None in other.parts:
            return NotImplemented
        return self.parts < other.parts


class Dated:
    def __init__(self):
        self._date = None

    @property
    def date(self) -> Optional[Date]:
        return self._date

    @date.setter
    def date(self, date: Date):
        self._date = date


class Note:
    def __init__(self, text: str):
        self._text = text

    @property
    def text(self):
        return self._text


class Identifiable:
    def __init__(self, id: str):
        self._id = id

    @property
    def id(self) -> str:
        return self._id


class Described:
    def __init__(self):
        self._description = None

    @property
    def description(self) -> Optional[str]:
        return self._description

    @description.setter
    def description(self, description: str):
        self._description = description


class Link:
    def __init__(self, uri: str, label: Optional[str]):
        self._uri = uri
        self._label = label

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def label(self) -> str:
        return self._label if self._label else self._uri


class File(Identifiable, Described):
    def __init__(self, file_id: str, path: str):
        Identifiable.__init__(self, file_id)
        Described.__init__(self)
        self._path = path
        self._type = None
        self._notes = []
        self._entities = EventHandlingSet(lambda entity: entity.files.add(self),
                                          lambda entity: entity.files.remove(self))

    @property
    def path(self):
        return self._path

    @property
    def type(self) -> Optional[str]:
        return self._type

    @type.setter
    def type(self, file_type: str):
        self._type = file_type

    @property
    def name(self) -> str:
        return basename(self._path)

    @property
    def basename(self) -> str:
        return splitext(self._path)[0]

    @property
    def extension(self) -> Optional[str]:
        extension = splitext(self._path)[1][1:]
        return extension if extension else None

    @property
    def notes(self) -> List[Note]:
        return self._notes

    @notes.setter
    def notes(self, notes: List[Note]):
        self._notes = notes

    @property
    def entities(self) -> Iterable:
        return self._entities

    @entities.setter
    def entities(self, entities: Iterable):
        self._entities.replace(entities)


class HasFiles:
    def __init__(self):
        self._files = EventHandlingSet(lambda file: file.entities.add(self),
                                       lambda file: file.entities.remove(self))

    @property
    def files(self) -> Iterable:
        return self._files

    @files.setter
    def files(self, files: Iterable):
        self._files.replace(files)


class Reference(Identifiable, Dated, HasFiles):
    def __init__(self, reference_id: str, name: str):
        Identifiable.__init__(self, reference_id)
        HasFiles.__init__(self)
        self._name = name
        self._link = None
        self._contained_by = None

        def handle_contains_addition(reference):
            reference.referrers = self

        def handle_contains_removal(reference):
            reference.referrers = None

        self._contains = EventHandlingSet(
            handle_contains_addition, handle_contains_removal)

        self._referees = EventHandlingSet(lambda referee: referee.references.add(self),
                                          lambda referee: referee.references.remove(self))

    @property
    def contained_by(self):
        return self._contained_by

    @contained_by.setter
    def contained_by(self, reference):
        previous_reference = self._contained_by
        self._contained_by = reference
        if previous_reference is not None:
            previous_reference.contains.remove(self)
        if reference is not None:
            reference.contains.add(self)

    @property
    def contains(self) -> Iterable:
        return self._contains

    @property
    def referees(self) -> Iterable:
        return self._referees

    @referees.setter
    def referees(self, referees: Iterable):
        self._referees.replace(referees)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name

    @property
    def link(self) -> Optional[Link]:
        return self._link

    @link.setter
    def link(self, link: Optional[Link]):
        self._link = link


class Referenced:
    def __init__(self):
        self._references = EventHandlingSet(lambda references: references.referees.add(self),
                                            lambda references: references.referees.remove(self))

    @property
    def references(self) -> Iterable:
        return self._references

    @references.setter
    def references(self, references: Iterable):
        self._references.replace(references)


class Place(Identifiable):
    def __init__(self, place_id: str, name: str):
        Identifiable.__init__(self, place_id)
        self._name = name
        self._coordinates = None

        def handle_event_addition(event: Event):
            event.place = self

        def handle_event_removal(event: Event):
            event.place = None

        self._events = EventHandlingSet(
            handle_event_addition, handle_event_removal)
        self._enclosed_by = None

        def handle_encloses_addition(place):
            place.enclosed_by = self

        def handle_encloses_removal(place):
            place.enclosed_by = None

        self._encloses = EventHandlingSet(
            handle_encloses_addition, handle_encloses_removal)

    @property
    def name(self) -> str:
        return self._name

    @property
    def coordinates(self) -> Point:
        return self._coordinates

    @coordinates.setter
    def coordinates(self, coordinates: Point):
        self._coordinates = coordinates

    @property
    def events(self) -> Iterable:
        return self._events

    @property
    def enclosed_by(self):
        return self._enclosed_by

    @enclosed_by.setter
    def enclosed_by(self, place):
        previous_place = self._enclosed_by
        self._enclosed_by = place
        if previous_place is not None:
            previous_place.encloses.remove(self)
        if place is not None:
            place.encloses.add(self)

    @property
    def encloses(self) -> Iterable:
        return self._encloses


class Event(Identifiable, Dated, HasFiles, Referenced):
    class Type(Enum):
        BIRTH = 'birth'
        BAPTISM = 'baptism'
        CREMATION = 'cremation'
        DEATH = 'death'
        BURIAL = 'burial'
        MARRIAGE = 'marriage'
        RESIDENCE = 'residence'

    def __init__(self, event_id: str, entity_type: Type, date: Optional[Date] = None, place: Optional[Place] = None):
        Identifiable.__init__(self, event_id)
        Dated.__init__(self)
        HasFiles.__init__(self)
        Referenced.__init__(self)
        self._date = date
        self._place = place
        self._type = entity_type
        self._people = EventHandlingSet(lambda person: person.events.add(self),
                                        lambda person: person.events.remove(self))

    @property
    def place(self) -> Optional[Place]:
        return self._place

    @place.setter
    def place(self, place: Optional[Place]):
        previous_place = self._place
        self._place = place
        if previous_place is not None:
            previous_place.events.remove(self)
        if place is not None:
            place.events.add(self)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, event_type: Type):
        self._type = event_type

    @property
    def people(self):
        return self._people

    @people.setter
    def people(self, people):
        self._people.replace(people)


class Person(Identifiable, HasFiles, Referenced):
    def __init__(self, person_id: str, individual_name: str = None, family_name: str = None):
        Identifiable.__init__(self, person_id)
        HasFiles.__init__(self)
        Referenced.__init__(self)
        self._individual_name = individual_name
        self._family_name = family_name
        self._events = EventHandlingSet(lambda event: event.people.add(self),
                                        lambda event: event.people.remove(self))
        self._parents = EventHandlingSet(lambda parent: parent.children.add(self),
                                         lambda parent: parent.children.remove(self))
        self._children = EventHandlingSet(lambda child: child.parents.add(self),
                                          lambda child: child.parents.remove(self))
        self._private = None

    @property
    def individual_name(self) -> Optional[str]:
        return self._individual_name

    @individual_name.setter
    def individual_name(self, name: str):
        self._individual_name = name

    @property
    def family_name(self) -> Optional[str]:
        return self._family_name

    @family_name.setter
    def family_name(self, name: str):
        self._family_name = name

    @property
    def names(self) -> Tuple[str, str]:
        return self._family_name or '', self._individual_name or ''

    @property
    def events(self) -> Iterable:
        return self._events

    @events.setter
    def events(self, events: Iterable):
        self._events.replace(events)

    @property
    def birth(self) -> Optional[Event]:
        for event in self._events:
            if event.type == Event.Type.BIRTH:
                return event
        return None

    @property
    def death(self) -> Optional[Event]:
        for event in self._events:
            if event.type == Event.Type.DEATH:
                return event
        return None

    @property
    def parents(self) -> Iterable:
        return self._parents

    @parents.setter
    def parents(self, parents: Iterable):
        self._parents.replace(parents)

    @property
    def children(self) -> Iterable:
        return self._children

    @children.setter
    def children(self, children: Iterable):
        self._children.replace(children)

    @property
    def siblings(self):
        siblings = set()
        for parent in self._parents:
            for sibling in parent.children:
                if sibling != self:
                    siblings.add(sibling)
        return siblings

    @property
    def private(self) -> Optional[bool]:
        return self._private

    @private.setter
    def private(self, private: Optional[bool]):
        self._private = private


class Ancestry:
    def __init__(self):
        self._files = {}
        self._people = {}
        self._places = {}
        self._events = {}
        self._references = {}

    @property
    def files(self) -> Dict[str, File]:
        return self._files

    @files.setter
    def files(self, files: Dict[str, File]):
        self._files = files

    @property
    def people(self) -> Dict[str, Person]:
        return self._people

    @people.setter
    def people(self, people: Dict[str, Person]):
        self._people = people

    @property
    def places(self) -> Dict[str, Place]:
        return self._places

    @places.setter
    def places(self, places: Dict[str, Place]):
        self._places = places

    @property
    def events(self) -> Dict[str, Event]:
        return self._events

    @events.setter
    def events(self, events: Dict[str, Event]):
        self._events = events

    @property
    def references(self) -> Dict[str, Reference]:
        return self._references

    @references.setter
    def references(self, references: Dict[str, Reference]):
        self._references = references
