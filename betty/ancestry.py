from enum import Enum
from functools import total_ordering
from os.path import splitext, basename
from typing import Dict, Optional, List, Iterable, Set

from geopy import Point

from betty.locale import Localized, Datey


class EventHandlingSet:
    def __init__(self, addition_handler=None, removal_handler=None):
        self._values = []
        self._addition_handler = addition_handler
        self._removal_handler = removal_handler

    @property
    def list(self) -> List:
        return list(self._values)

    def add(self, *values):
        for value in values:
            self._add_one(value)

    def _add_one(self, value):
        if value in self._values:
            return
        self._values.append(value)
        if self._addition_handler is not None:
            self._addition_handler(value)

    def remove(self, value):
        if value not in self._values:
            return
        self._values.remove(value)
        if self._removal_handler is not None:
            self._removal_handler(value)

    def replace(self, values: Iterable):
        for value in list(self._values):
            self.remove(value)
        for value in values:
            self.add(value)

    def __iter__(self):
        return self._values.__iter__()

    def __len__(self):
        return len(self._values)


class Dated:
    def __init__(self):
        self._date = None

    @property
    def date(self) -> Optional[Datey]:
        return self._date

    @date.setter
    def date(self, date: Datey):
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
    def __init__(self, url: str, label: Optional[str] = None):
        self._url = url
        self._label = label

    @property
    def url(self) -> str:
        return self._url

    @property
    def label(self) -> str:
        return self._label if self._label else self._url


class HasLinks:
    def __init__(self):
        self._links = set()

    @property
    def links(self) -> Set[Link]:
        return self._links


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
    def path(self) -> str:
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


class Source(Identifiable, Dated, HasFiles, HasLinks):
    def __init__(self, source_id: str, name: str):
        Identifiable.__init__(self, source_id)
        Dated.__init__(self)
        HasFiles.__init__(self)
        HasLinks.__init__(self)
        self._name = name
        self._contained_by = None

        def handle_contains_addition(source):
            source.contained_by = self

        def handle_contains_removal(source):
            source.contained_by = None

        self._contains = EventHandlingSet(
            handle_contains_addition, handle_contains_removal)

        def handle_citations_addition(citation):
            citation.source = self

        def handle_citations_removal(citation):
            citation.source = None

        self._citations = EventHandlingSet(
            handle_citations_addition, handle_citations_removal)

    @property
    def contained_by(self):
        return self._contained_by

    @contained_by.setter
    def contained_by(self, source):
        previous_source = self._contained_by
        self._contained_by = source
        if previous_source is not None:
            previous_source.contains.remove(self)
        if source is not None:
            source.contains.add(self)

    @property
    def contains(self) -> Iterable:
        return self._contains

    @property
    def citations(self) -> Iterable:
        return self._citations

    @citations.setter
    def citations(self, citations: Iterable):
        self._citations.replace(citations)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name


class Citation(Identifiable, Described, HasFiles):
    def __init__(self, citation_id: str, source: Source):
        Identifiable.__init__(self, citation_id)
        HasFiles.__init__(self)
        Described.__init__(self)
        self._source = source
        source.citations.add(self)
        self._claims = EventHandlingSet(lambda claim: claim.citations.add(self),
                                        lambda claim: claim.citations.remove(self))

    @property
    def source(self) -> Source:
        return self._source

    @source.setter
    def source(self, source: Source):
        previous_source = self._source
        self._source = source
        if previous_source is not None:
            previous_source.citations.remove(self)
        if source is not None:
            source.citations.add(self)

    @property
    def claims(self) -> Iterable:
        return self._claims

    @claims.setter
    def claims(self, claims: Iterable):
        self._claims.replace(claims)


class HasCitations:
    def __init__(self):
        self._citations = EventHandlingSet(lambda citation: citation.claims.add(self),
                                           lambda citation: citation.claims.remove(self))

    @property
    def citations(self) -> Iterable:
        return self._citations

    @citations.setter
    def citations(self, citations: Iterable):
        self._citations.replace(citations)


class LocalizedName(Localized):
    def __init__(self, name: str, locale: Optional[str] = None):
        Localized.__init__(self)
        self._name = name
        self.locale = locale

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._name == other._name and self._locale == other._locale

    def __repr__(self):
        return '%s(%s, %s)' % (type(self).__name__, self._name, self._locale.__repr__())

    def __str__(self):
        return self._name

    @property
    def name(self) -> str:
        return self._name


class Place(Identifiable, HasLinks):
    def __init__(self, place_id: str, names: List[LocalizedName]):
        Identifiable.__init__(self, place_id)
        HasLinks.__init__(self)
        self._names = names
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
    def names(self) -> List[LocalizedName]:
        return self._names

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


class Presence:
    class Role(Enum):
        SUBJECT = 'subject'
        WITNESS = 'witness'
        ATTENDEE = 'attendee'

    def __init__(self, role: Role):
        self._role = role
        self._person = None
        self._event = None

    @property
    def role(self) -> 'Role':
        return self._role

    @property
    def person(self) -> 'Person':
        return self._person

    @person.setter
    def person(self, person: 'Person'):
        previous_person = self._person
        self._person = person
        if previous_person is not None:
            previous_person.presences.remove(self)
        if person is not None:
            person.presences.add(self)

    @property
    def event(self) -> 'Event':
        return self._event

    @event.setter
    def event(self, event: 'Event'):
        previous_event = self._event
        self._event = event
        if previous_event is not None:
            previous_event.presences.remove(self)
        if event is not None:
            event.presences.add(self)


class Event(Identifiable, Dated, HasFiles, HasCitations):
    class Type(Enum):
        BIRTH = 'birth'
        BAPTISM = 'baptism'
        CREMATION = 'cremation'
        DEATH = 'death'
        BURIAL = 'burial'
        MARRIAGE = 'marriage'
        MARRIAGE_BANNS = 'marriage-banns'
        RESIDENCE = 'residence'
        IMMIGRATION = 'immigration'
        EMIGRATION = 'emigration'

    def __init__(self, event_id: str, event_type: Type, date: Optional[Datey] = None, place: Optional[Place] = None):
        Identifiable.__init__(self, event_id)
        Dated.__init__(self)
        HasFiles.__init__(self)
        HasCitations.__init__(self)
        self._date = date
        self._place = place
        self._type = event_type

        def handle_presence_addition(presence):
            presence.event = self

        def handle_presence_removal(presence):
            presence.event = None

        self._presences = EventHandlingSet(
            handle_presence_addition, handle_presence_removal)

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
    def presences(self):
        return self._presences

    @presences.setter
    def presences(self, presences):
        self._presences.replace(presences)


@total_ordering
class IndividualName:
    def __init__(self, name: str = '', nick: str = ''):
        self._name = name
        self._nick = nick

    def __eq__(self, other):
        if not isinstance(other, IndividualName):
            return NotImplemented
        return self._name == other._name

    def __gt__(self, other):
        if not isinstance(other, IndividualName):
            return NotImplemented
        return self._name > other._name

    @property
    def name(self) -> str:
        return self._name

    @property
    def nick(self) -> Optional[str]:
        return self._nick


@total_ordering
class FamilyName:
    def __init__(self, name: str, prefix: str = ''):
        self._name = name
        self._prefix = prefix

    def __eq__(self, other):
        if not isinstance(other, FamilyName):
            return NotImplemented
        return self._name, self._prefix == other._name, other._prefix

    def __gt__(self, other):
        if not isinstance(other, FamilyName):
            return NotImplemented
        return self._name, self._prefix > other._name, other._prefix

    def __str__(self):
        if self._prefix is None:
            return self._name
        return '%s %s' % (self._prefix, self._name)

    @property
    def name(self) -> str:
        return self._name

    @property
    def prefix(self) -> str:
        return self._prefix


@total_ordering
class Name(HasCitations):
    def __init__(self, individual: Optional[IndividualName] = None, family: Optional[FamilyName] = None):
        HasCitations.__init__(self)
        self._individual = individual
        self._family = family

    def __eq__(self, other):
        if not isinstance(other, Name):
            return NotImplemented
        return self._family, self._individual == other._family, other._individual

    def __gt__(self, other):
        if not isinstance(other, Name):
            return NotImplemented
        return self._family, self._individual > other._family, other._individual

    @property
    def individual(self) -> IndividualName:
        return self._individual

    @property
    def family(self) -> FamilyName:
        return self._family


@total_ordering
class Person(Identifiable, HasFiles, HasCitations, HasLinks):
    def __init__(self, person_id: str):
        Identifiable.__init__(self, person_id)
        HasFiles.__init__(self)
        HasCitations.__init__(self)
        HasLinks.__init__(self)
        self._name = None
        self._alternative_names = []
        self._parents = EventHandlingSet(lambda parent: parent.children.add(self),
                                         lambda parent: parent.children.remove(self))
        self._children = EventHandlingSet(lambda child: child.parents.add(self),
                                          lambda child: child.parents.remove(self))
        self._private = None

        def handle_presence_addition(presence):
            presence.person = self

        def handle_presence_removal(presence):
            presence.person = None

        self._presences = EventHandlingSet(
            handle_presence_addition, handle_presence_removal)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.id == other.id

    def __gt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.id > other.id

    @property
    def name(self) -> Optional[Name]:
        return self._name

    @name.setter
    def name(self, name: Name):
        self._name = name

    @property
    def alternative_names(self) -> List[Name]:
        return self._alternative_names

    @alternative_names.setter
    def alternative_names(self, names: Iterable[Name]):
        self._alternative_names = list(names)

    @property
    def presences(self) -> Iterable:
        return self._presences

    @presences.setter
    def presences(self, presences: Iterable):
        self._presences.replace(presences)

    @property
    def start(self) -> Optional[Event]:
        for event_type in [Event.Type.BIRTH, Event.Type.BAPTISM]:
            for presence in self.presences:
                if presence.event.type == event_type and presence.role == Presence.Role.SUBJECT:
                    return presence.event
        return None

    @property
    def end(self) -> Optional[Event]:
        for event_type in [Event.Type.DEATH, Event.Type.BURIAL]:
            for presence in self.presences:
                if presence.event.type == event_type and presence.role == Presence.Role.SUBJECT:
                    return presence.event
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
    def siblings(self) -> List:
        siblings = []
        for parent in self._parents:
            for sibling in parent.children:
                if sibling != self and sibling not in siblings:
                    siblings.append(sibling)
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
        self._sources = {}
        self._citations = {}

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
    def sources(self) -> Dict[str, Source]:
        return self._sources

    @sources.setter
    def sources(self, sources: Dict[str, Source]):
        self._sources = sources

    @property
    def citations(self) -> Dict[str, Citation]:
        return self._citations

    @citations.setter
    def citations(self, citations: Dict[str, Citation]):
        self._citations = citations
