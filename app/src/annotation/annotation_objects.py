r"""
This module contains the dataclasses used to represent annotations:
- BoundingBox: A bounding box for an entity in an image.
- Entity: Represents a document entity on a page. An annotion consists of a
    bounding box, and the entity_id corresponding to entity class.
- Word: Represents a single word on a page
- AnnotatedPage: Represents a page with annotations and text.
- AnnotatedDocument: Represents a document consisting of pages with annotations
    and text.
"""
import dataclasses
from datetime import datetime
import hashlib
import string
from typing import List, Tuple, Union, Dict, Any

from orm.models import DocMetadataRecordDB, PageMetadataRecordDB

__all__ = [
    "BoundingBox",
    "Entity",
    "Word",
    "DocumentText",
    "AnnotatedPage",
    "AnnotatedDocument"
]

TRANSLATION_TABLE = str.maketrans(
    # These characters
    string.ascii_lowercase + string.ascii_uppercase,
    # Become these characters
    string.ascii_lowercase * 2,
    # These are deleted
    string.punctuation
)


def asdict(obj):
    """ convenience function to convert dataclass to dict, including the
    attributes specified in __add_to_dict__ """
    return {
        **dataclasses.asdict(obj),
        **{a: getattr(obj, a) for a in getattr(obj, '__add_to_dict__', {})}
    }


@dataclasses.dataclass
class BoundingBox:
    r""" A bounding box for an entity in an image. """
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self):
        if self.width < 0:
            raise ValueError("Width must be positive")
        if self.height < 0:
            raise ValueError("Height must be positive")

    def __repr__(self):
        return "BoundingBox(x={}, y={}, width={}, height={})".format(*self.box)

    def rescale(self, width_scale: float, height_scale: float):
        r""" Rescale the bounding box by the given scale factors.

        @param width_scale: scale factor for width
        @param height_scale: scale factor for height
        """
        self.x *= width_scale
        self.y *= height_scale
        self.width *= width_scale
        self.height *= height_scale

    @property
    def box(self) -> Tuple[float, float, float, float]:
        return self.x, self.y, self.width, self.height

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclasses.dataclass
class Entity:
    r""" Represents a document entity on a page. An annotion consists of a
    bounding box, and the entity_id corresponding to entity class.
    """
    doc_id: str
    page_id: str
    page_num: int
    entity_category: int
    bbox: BoundingBox

    __add_to_dict__ = {"id", "area"}

    def __post_init__(self):
        self.area = self.bbox.area

        # compute hash of representation for fast comparison. Note that this
        # also serves as a unique identifier for the entity.
        self.id = hashlib.sha1(self.__repr__().encode('utf-8')).hexdigest()

    def __repr__(self):
        # unambiguous representation of the object
        # ! important: this is used to compute the id, which uniquely
        # ! determines the object and which is used to compare / deduplicate
        # ! entities.
        obj_str = "Entity(doc_id={}, page_id={}, page_num={}, " \
                  "entity_category={}, bbox={})"
        return obj_str.format(self.doc_id, self.page_id, self.page_num,
                              self.entity_category, self.bbox.__repr__())

    @classmethod
    def from_dict(cls, d: Dict):
        return cls(
            doc_id=d['doc_id'],
            page_id=d['page_id'],
            page_num=d['page_num'],
            entity_category=d['entity_category'],
            bbox=BoundingBox(**d['bbox']),
        )


@dataclasses.dataclass
class Word:
    r""" Represents a single word on a page

    Attributes:
        doc_id: id of the document the word belongs to
        entity_ids: id of the entity the word belongs to
        entity_categories: category of the entity the word belongs to
        page_num: page number of the page the word belongs to
        bbox: bounding box of the word
        text: text of the word
        upright: whether the word is upright or not
        direction: direction of the word
    """
    doc_id: str
    entity_ids: List[str]
    entity_categories: List[int]
    page_num: int
    bbox: BoundingBox
    text: str
    upright: bool
    direction: int

    def __post_init__(self):
        self.area = self.bbox.area

    @classmethod
    def from_dict(cls, d: Dict):
        return cls(
            doc_id=d['doc_id'],
            entity_ids=d['entity_ids'],
            entity_categories=d['entity_categories'],
            page_num=d['page_num'],
            bbox=BoundingBox(**d['bbox']),
            text=d['text'],
            upright=d['upright'],
            direction=d['direction']
        )


@dataclasses.dataclass
class DocumentText:
    text: str

    def __post_init__(self):
        self.num_words = len(self.text.translate(TRANSLATION_TABLE).split())
        self.num_chars = len(self.text)
        self.num_alph_chars = sum(1 for s in self.text if s.isalpha())
        self.num_numeric_chars = sum(1 for s in self.text if s.isnumeric())
        self.num_alphnum_chars = sum(1 for s in self.text if s.isalnum())

        if self.num_chars == 0:
            self.alnum_prop = 0
        else:
            self.alnum_prop = self.num_alphnum_chars / self.num_chars

        if self.num_numeric_chars == 0:
            self.alph_to_num_ratio = 0
        else:
            self.alph_to_num_ratio = \
                self.num_alph_chars / self.num_numeric_chars


@dataclasses.dataclass
class AnnotatedPage:
    doc_id: str
    page_id: str
    page_text: DocumentText
    words: List[Word]
    entities: Dict[int, List[Entity]]
    metadata: PageMetadataRecordDB

    def __post_init__(self):
        self._metadata_serialized = orm_to_json_dict(self.metadata)

    def words_to_json(self) -> Dict[str, Any]:
        return {
            "words": [asdict(w) for w in self.words],
            "metadata": self._metadata_serialized
        }

    def entities_to_json(self) -> Dict[str, Any]:
        return {
            "entities": {
                entity_category: [asdict(e) for e in entity_list]
                for entity_category, entity_list in self.entities.items()
            },
            "metadata": self._metadata_serialized
        }

    def text_to_json(self) -> Dict[str, Any]:
        return {
            "text": self.page_text.text,
            "metadata": self._metadata_serialized
        }

    def meta_to_json(self) -> Dict[str, Any]:
        return self._metadata_serialized


@dataclasses.dataclass
class AnnotatedDocument:
    doc_id: str
    text: DocumentText
    pages: List[AnnotatedPage]
    metadata: DocMetadataRecordDB

    def __post_init__(self):
        self._metadata_serialized = orm_to_json_dict(self.metadata)

    def text_to_json(self) -> Dict[str, Any]:
        return {
            "text": self.text.text,
            "metadata": self._metadata_serialized
        }

    def meta_to_json(self) -> Dict[str, Any]:
        return self._metadata_serialized


def orm_to_json_dict(
        meta_record: Union[DocMetadataRecordDB, PageMetadataRecordDB]
) -> Dict:
    def _datetime_to_str(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    return {
        key: _datetime_to_str(getattr(meta_record, key))
        for key in meta_record.__class__.__table__.columns.keys()
    }
