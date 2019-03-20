from unittest import TestCase

from betty.ancestry import EventHandlingSet, Person, Family, Event, Place


class EventHandlingSetTest(TestCase):
    def test_with_handler(self):
        reference = []

        def addition_handler(added_value):
            reference.append(added_value)

        def removal_handler(removed_value):
            reference.remove(removed_value)

        sut = EventHandlingSet(addition_handler, removal_handler)
        value = 'A valuable value'
        sut.add(value)
        self.assertEquals(list(sut), [value])
        self.assertEquals(reference, [value])
        sut.remove(value)
        self.assertEquals(list(sut), [])
        self.assertEquals(reference, [])

    def test_without_handler(self):
        sut = EventHandlingSet()
        value = 'A valuable value'
        sut.add(value)
        self.assertEquals(list(sut), [value])
        sut.remove(value)
        self.assertEquals(list(sut), [])


class PersonTest(TestCase):
    def test_ancestor_families_should_sync_references(self):
        family = Family('1')
        sut = Person('1')
        sut.ancestor_families.add(family)
        self.assertEquals(list(sut.ancestor_families), [family])
        self.assertEquals(list(family.parents), [sut])
        sut.ancestor_families.remove(family)
        self.assertEquals(list(sut.ancestor_families), [])
        self.assertEqual(list(family.parents), [])

    def test_descendant_family_should_sync_references(self):
        family = Family('1')
        sut = Person('1')
        sut.descendant_family = family
        self.assertEquals(sut.descendant_family, family)
        self.assertEquals(list(family.children), [sut])
        sut.descendant_family = None
        self.assertIsNone(sut.descendant_family)
        self.assertEquals(list(family.children), [])

    def test_children_without_ancestor_families(self):
        sut = Person('person')
        self.assertEquals(sut.children, [])

    def test_children_with_multiple_ancestor_families(self):
        child_1_1 = Person('1_1')
        child_1_2 = Person('1_2')
        family_1 = Family('1')
        family_1.children = [child_1_1, child_1_2]

        child_2_1 = Person('2_1')
        child_2_2 = Person('2_2')
        family_2 = Family('2')
        family_2.children = [child_2_1, child_2_2]

        sut = Person('person')
        sut.ancestor_families = [family_1, family_2]

        self.assertCountEqual(
            sut.children, [child_1_1, child_1_2, child_2_1, child_2_2])

    def test_children_without_descendant_family(self):
        sut = Person('person')
        self.assertEquals(sut.parents, [])

    def test_children_with_descendant_family(self):
        parent_1 = Person('1')
        parent_2 = Person('2')
        family = Family('1')
        family.parents = [parent_1, parent_2]

        sut = Person('person')
        sut.descendant_family = family

        self.assertCountEqual(sut.parents, [parent_1, parent_2])


class FamilyTest(TestCase):
    def test_parents_should_sync_references(self):
        parent = Person('1')
        sut = Family('1')
        sut.parents.add(parent)
        self.assertEquals(list(sut.parents), [parent])
        self.assertEquals(list(parent.ancestor_families), [sut])
        sut.parents.remove(parent)
        self.assertEquals(list(sut.parents), [])
        self.assertEquals(list(parent.ancestor_families), [])

    def test_children_should_sync_references(self):
        child = Person('1')
        sut = Family('1')
        sut.children.add(child)
        self.assertEquals(list(sut.children), [child])
        self.assertEquals(child.descendant_family, sut)
        sut.children.remove(child)
        self.assertEquals(list(sut.children), [])
        self.assertEquals(child.descendant_family, None)


class PlaceTest(TestCase):
    def test_events_should_sync_references(self):
        event = Event('1', Event.Type.BIRTH)
        sut = Place('1')
        sut.events.add(event)
        self.assertIn(event, sut.events)
        self.assertEquals(sut, event.place)


class EventTest(TestCase):
    def test_place_should_sync_references(self):
        place = Place('1')
        sut = Event('1', Event.Type.BIRTH)
        sut.place = place
        self.assertEquals(place, sut.place)
        self.assertIn(sut, place.events)
        sut.place = None
        self.assertEquals(None, sut.place)
        self.assertNotIn(sut, place.events)
