"""Jinja templating for vsdx documents.

Static methods defined here are bound onto VisioFile at import time so the
public API (vis.jinja_render_vsdx(context)) is unchanged.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from jinja2 import Template

from .logging_support import get_logger
from .pages import Page
from .shapes import Shape

logger = get_logger(__name__)


class JinjaTemplatingMixin:
    def jinja_render_vsdx(self, context: dict):
        """Transform a template VisioFile object using the Jinja language
        The method updates the VisioFile object loaded from the template file, so does not return any value
        Note: vsdx specific extensions are available such as `{% for item in list %}` statements with no `{% endfor %}`

        :param context: A dictionary containing values that can be accessed by the Jinja processor
        :type context: dict

        :return: None
        """
        # parse each shape in each page as Jinja2 template with context
        pages_to_remove = []  # list of pages to be removed after loop
        for page in self.pages:  # type: Page
            # check if page should be removed
            if JinjaTemplatingMixin.jinja_page_showif(page, context):
                loop_shape_ids = list()
                for shapes_by_id in page._shapes:  # type: Shape
                    JinjaTemplatingMixin.jinja_render_shape(shape=shapes_by_id, context=context, loop_shape_ids=loop_shape_ids)

                source = ET.tostring(page.xml.getroot(), encoding="unicode")
                source = JinjaTemplatingMixin.unescape_jinja_statements(source)  # unescape chars like < and > inside {%...%}
                template = Template(source)
                output = template.render(context)
                page.xml = ET.ElementTree(ET.fromstring(output))  # create ElementTree from Element created from output

                # update loop shape IDs which have been duplicated by Jinja template
                page.set_max_ids()
                for shape_id in loop_shape_ids:
                    shapes_by_id = page._find_shapes_by_id(shape_id)  # type: List[Shape]
                    if shapes_by_id and len(shapes_by_id) > 1:
                        delta = 0
                        for shape in shapes_by_id[1:]:  # from the 2nd onwards - leaving original unchanged
                            # increment each new shape duplicated by the jinja loop
                            self.increment_sub_shape_ids(shape, page)
                            delta += shape.height  # automatically move each duplicate down
                            shape.move(0, -delta)  # move duplicated shapes so they are visible
            else:
                # note page to remove after this loop has completed
                pages_to_remove.append(page)
        # remove pages after processing
        for p in pages_to_remove:
            logger.debug("Removing page:'%s' index:%s", p.name, p.index_num)
            self.remove_page_by_index(p.index_num)

    @staticmethod
    def jinja_render_shape(shape: Shape, context: dict, loop_shape_ids: list):
        prev_shape = None
        for s in shape.child_shapes:  # type: Shape
            # manage for loops in template
            loop_shape_id = JinjaTemplatingMixin.jinja_create_for_loop_if(s, prev_shape)
            if loop_shape_id:
                loop_shape_ids.append(loop_shape_id)
            prev_shape = s
            # manage 'set self' statements
            JinjaTemplatingMixin.jinja_set_selfs(s, context)
            JinjaTemplatingMixin.jinja_render_shape(shape=s, context=context, loop_shape_ids=loop_shape_ids)

    @staticmethod
    def jinja_set_selfs(shape: Shape, context: dict):
        # apply any {% self self.xxx = yyy %} statements in shape properties
        jinja_source = shape.text
        matches = re.findall(r"{% set self.(.*?)\s?=\s?(.*?) %}", jinja_source)  # non-greedy search for all {%...%} strings
        for m in matches:  # type: tuple  # expect ('property', 'value') such as ('x', '10') or ('y', 'n*2')
            property_name = m[0]
            value = "{{ " + m[1] + " }}"  # Jinja to be processed
            # todo: replace any self references in value with actual value - i.e. {% set self.x = self.x+1 %}
            self_refs = re.findall(r"self.(.*)[\s+-/*//]?", m[1])  # greedy search for all self.? between +, -, *, or /
            for self_ref in self_refs:  # type: tuple  # expect ('property', 'value') such as ('x', '10') or ('y', 'n*2')
                ref_val = str(shape.__getattribute__(self_ref[0]))
                value = value.replace("self." + self_ref[0], ref_val)
            # use Jinja template to calculate any self refs found
            template = Template(value)  # value might be '{{ 1.0+2.4*3 }}'
            value = template.render(context)
            if property_name in ["x", "y"]:
                shape.__setattr__(property_name, value)

        # remove any {% set self %} statements, leaving any remaining text
        matches = re.findall("{% set self.*?%}", jinja_source)
        for m in matches:
            jinja_source = jinja_source.replace(m, "")  # remove Jinja 'set self' statement
        shape.text = jinja_source

    @staticmethod
    def unescape_jinja_statements(jinja_source):
        # unescape any text between {% ... %}
        jinja_source_out = jinja_source
        matches = re.findall("{%(.*?)%}", jinja_source)  # non-greedy search for all {%...%} strings
        for m in matches:
            unescaped = m.replace("&gt;", ">").replace("&lt;", "<")
            jinja_source_out = jinja_source_out.replace(m, unescaped)
        return jinja_source_out

    @staticmethod
    def jinja_create_for_loop_if(shape: Shape, previous_shape: Shape | None):
        # update a Shapes tag where text looks like a jinja {% for xxxx %} loop
        # move text to start of Shapes tag and add {% endfor %} at end of tag
        text = shape.text

        # use regex to find all loops
        jinja_loops = re.findall(r"{% for\s(.*?)\s%}", text)

        for loop in jinja_loops:
            jinja_loop_text = f"{{% for {loop} %}}"
            # move the for loop to start of shapes element (just before first Shape element)
            if previous_shape:
                if previous_shape.xml.tail:
                    previous_shape.xml.tail += jinja_loop_text
                else:
                    previous_shape.xml.tail = jinja_loop_text  # add jinja loop text after previous shape, before this element
            else:
                if shape.parent.xml.text:
                    shape.parent.xml.text += jinja_loop_text
                else:
                    shape.parent.xml.text = jinja_loop_text  # add jinja loop at start of parent, just before this element
            shape.text = shape.text.replace(jinja_loop_text, "")  # remove jinja loop from <Text> tag in element

            # add closing 'endfor' to just inside the shapes element, after last shape
            if shape.xml.tail:  # extend or set text at end of Shape element
                shape.xml.tail += "{% endfor %}"
            else:
                shape.xml.tail = "{% endfor %}"

        jinja_show_ifs = re.findall(r"{% showif\s(.*?)\s%}", text)  # find all showif statements
        # jinja_show_if - translate non-standard {% showif statement %} to valid jinja if statement
        for show_if in jinja_show_ifs:
            jinja_show_if = f"{{% if {show_if} %}}"  # translate to actual jinja if statement
            # move the for loop to start of shapes element (just before first Shape element)
            if previous_shape:
                previous_shape.xml.tail = (
                    str(previous_shape.xml.tail or "") + jinja_show_if
                )  # add jinja loop text after previous shape, before this element
            else:
                shape.parent.xml.text = (
                    str(shape.parent.xml.text or "") + jinja_show_if
                )  # add jinja loop at start of parent, just before this element

            # remove original jinja showif from <Text> tag in element
            shape.text = shape.text.replace(f"{{% showif {show_if} %}}", "")

            # add closing 'endfor' to just inside the shapes element, after last shape
            if shape.xml.tail:  # extend or set text at end of Shape element
                shape.xml.tail += "{% endif %}"
            else:
                shape.xml.tail = "{% endif %}"

        if jinja_loops:
            return shape.ID  # return shape ID if it is a loop, so that duplicate shape IDs can be updated

    @staticmethod
    def jinja_page_showif(page: Page, context: dict):
        text = page.name
        jinja_source = re.findall(r"{% showif\s(.*?)\s%}", text)
        if len(jinja_source):
            # process last matching value
            template_source = "{{ " + jinja_source[-1] + " }}"
            template = Template(template_source)  # value might be '{{ 1.0+2.4*3 }}'
            value = template.render(context)
            # is the value truthy - i.e. not 0, False, or empty string, tuple, list or dict
            logger.debug(
                "jinja_page_showif(context=%s) statement: %s returns: %s %s", context, template_source, type(value), value
            )
            if value in ["False", "0", "", "()", "[]", "{}"]:
                logger.debug("value in ['False', '0', '', '()', '[]', '{}']")
                return False  # page should be hidden
            # remove jinja statement from page name
            jinja_statement = re.match("{%.*?%}", page.name)[0]
            page.name = page.name.replace(jinja_statement, "")
        return True  # page should be left in
