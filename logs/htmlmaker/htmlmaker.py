import os
from typing import Callable, Iterable, Iterator, List, Optional, Union

FILE_DIR = os.path.dirname(__file__)
DEF_TEMPLATE = f"{FILE_DIR }/html_template.html.templ"
DEF_CSS = f"{FILE_DIR }/style.css"
DEF_JS = f"{FILE_DIR }/js.js"


class HtmlMaker:
    """Allow making simple html files. Supports:
        - appending new html content from string
        - creating selection buttons, which hide/show some content"""

    def __init__(
        self,
        template: Optional[str] = None,
        css: str = "",
        js: str = "",
    ):
        """Parameters
        ----------
        template: str, optional
            default: `None`; template for the html document.
            The document has to contain these replacement fields:
            `{content}`, `{js}` and `{css}`.
            If `None` then simple default template will be used. 
        css: str, optional
            default: `""`; css styles to be added
        js: str, Optional
            default: `""`; javascript to be added

        """
        self.content: List[str] = []
        self._id: int = 0

        if template:
            self.template = template
        else:
            with open(DEF_TEMPLATE, "r") as f:
                self.template = f.read()

        if css:
            css += '\n'

        with open(DEF_CSS, "r") as f:
            self.css = css + f.read()
            
        if js:
            js += '\n'

        with open(DEF_JS, "r") as f:
            self.js = js + f.read()

    def append(self, new_content: str):
        """Appends `new_content` to the html content of given object.

        Note
        ----
        New lines between appended contents are autoamticaly added
        """
        self.content.append(new_content)

    def extend(self, new_content: Iterable[str]):
        """Extends the html content of given object
        with `new_content`.

        Note
        ----
        New lines between appended contents are autoamticaly added
        """
        self.content.extend(new_content)

    def _get_id(self) -> str:
        """Returns decimal digit which is unique for every call.
         Starts with 0. """
        self._id += 1
        return str(self._id)

    def print_sel_buttons(
        self, texts: List[str], classes: List[List[str]]
    ) -> List[str]:
        """Appends `len(texts)` of selection buttons to the html document of given object.
        Each selection button is conneted to a created unique class 
        and will work as a show/hide button for every html object with this class.

        Attributes
        ----------
        texts: List[str]
            texts for selection buttons
        classes: List[List[str]]
            each i-th item (List[str]) contains classes for i-th sellection button

        Returns
        -------
        List[str]
            list of `len(texts)` unique classes paired with created selection buttons
        """
        uniq_classes: List[str] = []

        for i in range(len(texts)):
            uniq_class = "class" + self._get_id()
            uniq_classes.append(uniq_class)
            self.append(
                make_selection_button(uniq_class, texts[i], classes[i] + [uniq_class])
            )
        return uniq_classes

    def print_selection(
        self, texts: List[str], classes: List[List[str]], label_text: str = "Select:"
    ) -> List[str]:
        """Appends `len(texts)` of selection buttons to the html document of given object
        and a label for these buttons.
        Each selection button is conneted to a created unique class 
        and will work as a show/hide button for every html object with this class.

        Attributes
        ----------
        texts: List[str]
            texts for selection buttons
        classes: List[List[str]]
            each i-th item (List[str]) contains classes for i-th sellection button
        label_text: str, optional
            default: `"Select:"`; text of the label

        Returns
        -------
        List[str]
            list of `len(texts)` unique classes paired with created selection buttons"""
        self.append(f"<label class='selection_label'>{label_text}</label>\n")
        return self.print_sel_buttons(texts, classes)

    def html(self) -> str:
        """Returns whole html documnet"""
        content = "\n".join(self.content)
        return self.template.format(css=self.css, content=content, js=self.js)
    

def make_table(
    caption: str,
    header: Iterable[str],
    content: Iterable[Iterable[str]],
    id: Optional[str] = None,
    table_classes: Optional[Iterable[str]] = None,
    td_attribs: Iterable[Iterable[Union[str, Iterable[str]]]] = [],
) -> str:
    """Creates html table
    
    Parameters
    ----------
    caption: str
        caption of the table
    header: Iterable[str]
        teable header
    content: Iterable[Iterable[str]]
        iterable of rows, where a row is
        iterable of table cell's content
    id: str, optional
        default: `None`; id for the table,
        if none then table will have no id
    table_classes: Iterable[str], optional
        default: `None`; if not `None` then 
        contains classes for the table
    td_attribs: Iterable[Iterable[Union[str, Iterable[str]]]]
        default: `[]`; iterable of rows,
        where a row is a iterable of attributes for table cells in given row.
        The attributes for each cell is either string or iterable of strings.
        It is possible to provide iterable shorter than the 
        corresponding number of rows or cells in the row, in such case 
        no attributes will be added to elements for which no item in iterable remain.

    Returns
    -------
        the html table as a string
    """
    id_attr = f"id='{id}'" if id else ""
    table_clasess = f"class='{' '.join(table_classes)}'" if table_classes else ""

    rows = (
        make_table_row(row_data, attribs)
        for row_data, attribs in zip(content, extend_forever(td_attribs, []))
    )

    return (
        f"<table {id_attr} {table_clasess}>\n"
        f"<caption>{caption}</caption>\n<thead>\n"
        + make_table_header(header)
        + "\n</thead>\n<tbody>\n"
        + "\n".join(rows)
        + "\n</tbody>\n</table>"
    )


def decore_table_row(func: Callable[..., str]) -> str:
    def decoreated(*args, **kwargs):
        return "<tr>\n" + func(*args, **kwargs) + "\n</tr>"

    return decoreated


@decore_table_row
def make_table_header(content: Iterable[str]):
    return "<th>" + "</th>\n<th>".join(map(str, content)) + "</th>"


@decore_table_row
def make_table_row(content: Iterable[str], td_attribs: Iterable[Union[str, Iterable[str]]]):
    result = []

    for td_data, attribs in zip(content, extend_forever(td_attribs, "")):
        if not isinstance(attribs, str):
            attribs = ' '.join(attribs)
        result.append(f"<td {attribs}>{td_data}</td>")

    return "\n".join(result)


def make_selection_button(target_class: str, text: str, classes: List[str]) -> str:
    return (
        f"<button class='{' '.join(classes)}' "
        f"onclick='updateSelection(\"{target_class}\")'>"
        f"{text}</button>"
    )


def extend_forever(iter: Iterable, extander) -> Iterator:
    """At first yielding from `iter`,
    then yileding empty string for ever."""
    for attrib in iter:
        yield attrib

    while True:
        yield extander
