from typing import List, Optional, Iterable, Callable
import sys

DEF_TEMPLATE = "html_template.html"
DEF_CSS = "style.css"
DEF_JS = "js.js"
class Html_maker:
    __slots__ = ("content", "template", "css", "js", "_id")

    def __init__(self, template: Optional[str] = None,
                 css: Optional[str] = None, js: Optional[str] = None):
        # if template, css or js is None, default value is loaded form
        # "./html_template.html", "./style.css" or "./js.js"

        self.content: List[str] = []
        self._id = 0

        if template:
            self.template = template
        else:
            with open(DEF_TEMPLATE, "r") as f:
                self.template = f.read() 

        if css is not None:
            self.css = css
        else:
            with open(DEF_CSS, "r") as f:
                self.css = f.read()

        if js is not None:
            self.js = js
        else:
            with open(DEF_JS, "r") as f:
                self.js = f.read()


    def append(self, new_content: str):
        self.content.append(new_content)
    
    def extend(self, new_content: List[str]):
        self.content.extend(new_content)
    
    def get_id(self) -> str:
        self._id += 1
        return str(self._id)
    
    def print_sel_buttons(self,
                         texts: List[str],
                         classes: List[List[str]]
                         ) -> List[str] :
        uniq_classes: List[str] = []

        for i in range(len(texts)):
            uniq_class = "class" + self.get_id()
            uniq_classes.append(uniq_class)
            self.append(make_selection_button(uniq_class,
                                              texts[i],
                                              classes[i] + [uniq_class]))
        return uniq_classes

    def html(self) -> str:
        content = '\n'.join(self.content)
        return self.template.format(css=self.css, content=content, js=self.js)


def decore_table_row(func: Callable[..., str]) -> str:
    def decoreated(*args, **kwargs):
        return "<tr>\n"\
               + func(*args, **kwargs)\
               + "\n</n>"
    
    return decoreated


@decore_table_row
def make_table_header(content: Iterable[str]):
    return "<th>"\
           + "</th>\n<th>".join(map(str, content))\
           + "</th>"


@decore_table_row
def make_table_row(content: Iterable[str]):
    return "<td>"\
           + "</td>\n<td>".join(map(str, content))\
           + "</td>"


def make_table(caption: str,
               header: Iterable[str],
               content: Iterable[Iterable[str]],
               id: Optional[str]=None,
               classes: Optional[List[str]]=None ) -> str:
    id_attr = f"id='{id}'" if id else ""
    class_atrib = f"class='{' '.join(classes)}'" if classes else ""

    return f"<table {id_attr} {class_atrib}>\n"\
           f"<caption>{caption}</caption>\n"\
           + make_table_header(header)\
           + "\n"\
           + "\n".join(make_table_row(row) for row in content)\
           + "\n</table>"


def make_selection_button(target_class: str,
                          text: str,
                          classes: List[str]) -> str :
    return f"<button class='{' '.join(classes)}' "\
           f"onclick='updateSelection(\"{target_class}\")'>"\
           f"{text}</button>"



def test():
    html = Html_maker()
    html.append(make_table("Caption",
                           ["Item", "Price"],
                           [["Item1", "100"], ["Item2", "200"]],
                           "id_table1",

                           ))
    print(html.html())


if __name__ == '__main__':
    test()
        
