# -*- coding: utf-8 -*-
#

# Imports ###########################################################

import logging
import textwrap
from lxml import etree
from xml.etree import ElementTree as ET

from xblock.core import XBlock
from xblock.fields import List, Scope, String
from xblock.fragment import Fragment

from StringIO import StringIO

from .utils import render_template, AttrDict, load_resource


# Globals ###########################################################

log = logging.getLogger(__name__)


# Classes ###########################################################

class ImageExplorerBlock(XBlock): # pylint: disable=no-init
    """
    XBlock that renders an image with tooltips
    """
    display_name = String(
        display_name="Display Name",
        help="This name appears in the horizontal navigation at the top of the page.",
        scope=Scope.settings,
        default="Image Explorer"
    )

    opened_hotspots = List(
        help="Store hotspots opened by student, for completion",
        default=[],
        scope=Scope.user_state,
    )

    data = String(help="XML contents to display for this module", scope=Scope.content, default=textwrap.dedent("""\
        <image_explorer schema_version='1'>
            <background src="//upload.wikimedia.org/wikipedia/commons/thumb/a/ac/MIT_Dome_night1_Edit.jpg/800px-MIT_Dome_night1_Edit.jpg" />
            <description>
                <p>
                    Enjoy using the Image Explorer. Click around the MIT Dome and see what you find!
                </p>
            </description>
            <hotspots>
                <hotspot x='370' y='20' item-id='hotspotA'>
                    <feedback width='300' height='240'>
                        <header>
                            <p>
                                This is where many pranks take place. Below are some of the highlights:
                            </p>
                        </header>
                        <body>
                            <ul>
                                <li>Once there was a police car up here</li>
                                <li>Also there was a Fire Truck put up there</li>
                            </ul>
                        </body>
                    </feedback>
                </hotspot>
                <hotspot x='250' y='70' item-id="hotspotB">
                    <feedback width='440' height='400'>
                        <header>
                            <p>
                                Watch the Red Line subway go around the dome
                            </p>
                        </header>
                        <youtube video_id='dmoZXcuozFQ' width='400' height='300' />
                    </feedback>
                </hotspot>
            </hotspots>
        </image_explorer>
        """))

    def student_view(self, context):
        """
        Player view, displayed to the student
        """

        xmltree = etree.fromstring(self.data)

        description = self._get_description(xmltree)
        hotspots = self._get_hotspots(xmltree)
        background = self._get_background(xmltree)

        for hotspot in hotspots:
            width = 'width:{0}px'.format(hotspot.feedback.width) if hotspot.feedback.width else 'width:300px'
            height = 'height:{0}px'.format(hotspot.feedback.height) if hotspot.feedback.height else ''
            max_height = ''
            if not hotspot.feedback.height:
                max_height = 'max-height:{0}px'.format(hotspot.feedback.max_height) if \
                             hotspot.feedback.max_height else 'max-height:300px'

            hotspot.reveal_style = 'style="{0};{1};{2}"'.format(width, height, max_height)

        sprite_url = self.runtime.local_resource_url(self, 'public/images/hotspot-sprite.png')

        context = {
            'title': self.display_name,
            'description_html': description,
            'hotspots': hotspots,
            'background': background,
            'sprite_url': sprite_url,
        }


        fragment = Fragment()
        fragment.add_content(render_template('/templates/html/image_explorer.html', context))
        fragment.add_css(load_resource('public/css/image_explorer.css'))
        fragment.add_javascript(load_resource('public/js/image_explorer.js'))

        fragment.initialize_js('ImageExplorerBlock')

        return fragment


    @XBlock.json_handler
    def publish_event(self, data, suffix=''):

        try:
            event_type = data.pop('event_type')
        except KeyError:
            return {'result': 'error', 'message': 'Missing event_type in JSON data'}

        data['user_id'] = self.scope_ids.user_id
        data['component_id'] = self._get_unique_id()
        self.runtime.publish(self, event_type, data)

        if event_type == 'xblock.image-explorer.hotspot.opened':
            self.register_progress(data['item_id'])

        return {'result':'success'}

    def register_progress(self, hotspot_id):
        """
        Registers the completion of an hotspot, identified by id
        """
        xmltree = etree.fromstring(self.data)
        hotspots_ids = [h.item_id for h in self._get_hotspots(xmltree)]

        if not hotspots_ids \
                or hotspot_id not in hotspots_ids \
                or hotspot_id in self.opened_hotspots:
            return

        self.runtime.publish(self, 'progress', {})
        self.opened_hotspots.append(hotspot_id)
        log.debug(u'Opened hotspots so far for {}: {}'.format(self._get_unique_id(), self.opened_hotspots))

        opened_hotspots = [h for h in hotspots_ids if h in self.opened_hotspots]
        percent_completion = float(len(opened_hotspots)) / len(hotspots_ids)
        self.runtime.publish(self, 'grade', {
            'value': percent_completion,
            'max_value': 1,
        })
        log.debug(u'Sending grade for {}: {}'.format(self._get_unique_id(), percent_completion))

    def _get_unique_id(self):
        try:
            unique_id = self.location.name
        except AttributeError:
            # workaround for xblock workbench
            unique_id = self.parent.replace('.',  '-')
        return unique_id

    def studio_view(self, context):
        """
        Editing view in Studio
        """
        fragment = Fragment()
        fragment.add_content(render_template('/templates/html/image_explorer_edit.html', {
            'self': self,
        }))
        fragment.add_javascript(load_resource('public/js/image_explorer_edit.js'))

        fragment.initialize_js('ImageExplorerEditBlock')

        return fragment

    @XBlock.json_handler
    def studio_submit(self, submissions, suffix=''):

        self.display_name = submissions['display_name']
        xml_content = submissions['data']

        try:
            etree.parse(StringIO(xml_content))
            self.data = xml_content
        except etree.XMLSyntaxError as e:
            return {
                'result': 'error',
                'message': e.message
            }

        return {
            'result': 'success',
        }

    def _get_background(self, xmltree):
        """
        Parse the XML to get the information about the background image
        """
        background = xmltree.find('background')
        return AttrDict({
            'src': background.get('src'),
            'width': background.get('width'),
            'height': background.get('height')
        })

    def _inner_content(self, tag):
        """
        Helper met
        """
        if tag is not None:
            return u''.join(ET.tostring(e) for e in tag)
        return None

    def _get_description(self, xmltree):
        """
        Parse the XML to get the description information
        """
        description = xmltree.find('description')
        if description is not None:
            return self._inner_content(description)
        return None

    def _get_hotspots(self, xmltree):
        """
        Parse the XML to get the hotspot information
        """
        hotspots_element= xmltree.find('hotspots')
        hotspot_elements = hotspots_element.findall('hotspot')
        hotspots = []
        for index, hotspot_element in enumerate(hotspot_elements):
            feedback_element = hotspot_element.find('feedback')

            feedback = AttrDict()
            feedback.width = feedback_element.get('width')
            feedback.height = feedback_element.get('height')
            feedback.max_height = feedback_element.get('max-height')
            feedback.header = self._inner_content(feedback_element.find('header'))

            feedback.side = hotspot_element.get('side', 'auto')

            feedback.body = None
            body_element = feedback_element.find('body')
            if body_element is not None:
                feedback.type = 'text'
                feedback.body = self._inner_content(body_element)

            feedback.youtube = None
            youtube_element = feedback_element.find('youtube')
            if youtube_element is not None:
                feedback.type = 'youtube'
                feedback.youtube = AttrDict()
                feedback.youtube.video_id = youtube_element.get('video_id')
                feedback.youtube.width = youtube_element.get('width')
                feedback.youtube.height = youtube_element.get('height')

            hotspot = AttrDict()
            hotspot.item_id = hotspot_element.get('item-id')
            if hotspot.item_id is None:
                hotspot.item_id = 'hotspot' + str(index)
            hotspot.feedback = feedback
            hotspot.x = hotspot_element.get('x')
            hotspot.y = hotspot_element.get('y')

            hotspots.append(hotspot)

        return hotspots

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [("Image explorer scenario", "<vertical_demo><image-explorer/></vertical_demo>")]
