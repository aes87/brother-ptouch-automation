"""Media pack — bookshelf tags, archive boxes, CDs / records."""

from __future__ import annotations

from label_printer.templates.media.archive_box import ArchiveBoxTemplate
from label_printer.templates.media.bookshelf_tag import BookshelfTagTemplate
from label_printer.templates.media.cd_record import CdRecordTemplate
from label_printer.templates.pack import TemplatePack

PACK = TemplatePack(
    name="media",
    version="0.1.0",
    summary="Media labels — bookshelf tags, archive boxes, CDs/records.",
    templates=(
        BookshelfTagTemplate(),
        ArchiveBoxTemplate(),
        CdRecordTemplate(),
    ),
)
