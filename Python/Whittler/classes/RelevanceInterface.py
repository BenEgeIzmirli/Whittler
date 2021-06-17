from Whittler.classes.NestedObjectPointer import NestedObjectPointerInterface


class RelevanceInterface(NestedObjectPointerInterface):

    @property
    def relevant(self):
        return any(result.relevant for result in self.real_iter_values())

    def mark_irrelevant(self):
        for obj in self.real_iter_values():
            obj.mark_irrelevant()

    def mark_relevant(self):
        for obj in self.real_iter_values():
            obj.mark_relevant()

    def real_length(self):
        return len([e for e in self.real_iter_values()])

    def real_iter_values(self):
        raise NotImplementedError()

