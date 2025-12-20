# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2025 Bob Swift (rdswift)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

import re

from picard.config import get_config
from picard.plugin3.api import (
    OptionsPage,
    PluginApi,
    t_,
)

from .ui_options_performer_tag_replace import \
    Ui_PerformerTagReplaceOptionsPage


DEV_TESTING = False

pairs_split = re.compile(r"\r\n|\n\r|\n").split

USER_GUIDE_URL = 'https://picard-plugins-user-guides.readthedocs.io/en/latest/performer_tag_replace/user_guide.html'


class PerformerTagReplace:
    def __init__(self, api: PluginApi):
        self.api = api

    def _update_track_metadata(self, track_metadata, replacements):
        if 'recording' not in track_metadata or 'relations' not in track_metadata['recording']:
            return

        relations = []
        for relation in track_metadata['recording']['relations']:
            if 'type' in relation and relation['type'] in ['instrument', 'vocal']:

                if 'attributes' in relation:
                    attributes = []
                    for attribute in relation['attributes']:
                        for (original, replacement) in replacements:
                            attribute = attribute.replace(original, replacement)
                        attributes.append(attribute)
                    relation['attributes'] = attributes

                if 'attribute-ids' in relation:
                    attribute_ids = {}
                    for key, value in relation['attribute-ids'].items():
                        for (original, replacement) in replacements:
                            key = key.replace(original, replacement)
                        attribute_ids[key] = value
                    relation['attribute-ids'] = attribute_ids

                if 'attribute-credits' in relation:
                    attribute_credits = {}
                    for key, value in relation['attribute-credits'].items():
                        for (original, replacement) in replacements:
                            key = key.replace(original, replacement)
                        attribute_credits[key] = value
                    relation['attribute-credits'] = attribute_credits

            relations.append(relation)

        track_metadata['recording']['relations'] = relations

        return

    def performer_tag_replace(self, api, album, metadata, track_metadata, *args):
        replacements = []
        for pair in pairs_split(self.api.plugin_config["performer_tag_replacement_pairs"]):
            if "=" not in pair:
                continue
            original, replacement = pair.split('=', 1)
            if original:
                replacements.append((original, replacement))
                if DEV_TESTING:
                    self.api.logger.debug("Add pair: '%s' = '%s'", original, replacement,)
        if replacements:
            self._update_track_metadata(track_metadata, replacements)
            for key, values in list(metadata.rawitems()):
                if not key.startswith('performer:') and not key.startswith('~performersort:'):
                    continue
                mainkey, subkey = key.split(':', 1)
                if not subkey:
                    continue
                old_key = subkey
                for (original, replacement) in replacements:
                    subkey = subkey.replace(original, replacement)
                    if DEV_TESTING:
                        self.api.logger.debug("Applying pair: '%s' = '%s'", original, replacement,)
                        self.api.logger.debug("Updated key: '%s'", subkey,)
                if subkey != old_key:
                    self.api.logger.debug("Original key: '%s'  ==>  Replacement key: '%s'", old_key, subkey,)
                del metadata[key]
                newkey = ('%s:%s' % (mainkey, subkey,)).strip()
                for value in values:
                    old_value = value
                    if self.api.plugin_config["performer_tag_replace_performers"]:
                        for (original, replacement) in replacements:
                            value = value.replace(original, replacement)
                            if DEV_TESTING:
                                self.api.logger.debug("Applying pair: '%s' = '%s'", original, replacement,)
                                self.api.logger.debug("Updated value: '%s'", value,)
                        if value != old_value:
                            self.api.logger.debug("Original value: '%s'  ==>  Replacement value: '%s'", old_value, value,)
                    metadata.add_unique(newkey, value)
        else:
            self.api.logger.debug("No replacement pairs found.",)


class PerformerTagReplaceOptionsPage(OptionsPage):

    TITLE = t_("ui.title", "Performer Tag Replacement")

    def __init__(self, parent=None):
        super(PerformerTagReplaceOptionsPage, self).__init__(parent)
        self.ui = Ui_PerformerTagReplaceOptionsPage()
        self.ui.setupUi(self)
        self._add_translations()

    def _add_translations(self):
        self.ui.format_description.setText(
            "<html><head/><body><p>"
            + self.api.tr(
                "ui.format_description.p1",
                (
                    "These are the original / replacement pairs used to modify the keys for the performer tags. "
                    "Each pair must be entered on a separate line in the form:"
                )
            )
            + "</p><p><span style=\"font-weight:600;\">"
            + self.api.tr("ui.format_description.p2", "original character string=replacement character string")
            + "</span></p><p>"
            + self.api.tr(
                "ui.format_description.p3",
                (
                    "Blank lines and lines beginning with an equals sign (=) will be ignored. "
                    "Replacements will be made in the order they are found in the list. "
                    "An example for removing \"family\" from instrument names would be done using the following two lines:"
                )
            )
            + "</p>"
            + "<pre style=\"margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">"
            + "<span style=\"font-family:'Courier New'; font-size:10pt; font-weight:600;\">s family=ses<br/> family=s</span></pre>"
            + "</p><p>"
            + self.api.tr("ui.format_description.p4", "Note that the second line begins with a single space.")
            + "</p><p>"
            + self.api.tr("ui.format_description.p5", "Please see the {url}User Guide{end_url} for additional information.").format(
                url="<a href=\"" + USER_GUIDE_URL + "\"><span style=\"text-decoration: underline; color:#0000ff;\">",
                end_url="</span></a>",
            )
            + "</p></body></html>"
        )

    def load(self):
        # Enable external link
        self.ui.format_description.setOpenExternalLinks(True)

        # Replacement settings
        self.ui.performer_tag_replacement_pairs.setPlainText(self.api.plugin_config["performer_tag_replacement_pairs"])
        self.ui.performer_tag_replace_performers.setChecked(self.api.plugin_config["performer_tag_replace_performers"])

    def save(self):
        # Replacement settings
        self.api.plugin_config["performer_tag_replacement_pairs"] = self.ui.performer_tag_replacement_pairs.toPlainText()
        self.api.plugin_config["performer_tag_replace_performers"] = self.ui.performer_tag_replace_performers.isChecked()


def enable(api: PluginApi):
    """Called when plugin is enabled."""

    # Register configuration options
    api.plugin_config.register_option("performer_tag_replacement_pairs", ""),
    api.plugin_config.register_option("performer_tag_replace_performers", False),

    # Migrate settings from 2.x version if available
    migrate_settings(api)

    plugin = PerformerTagReplace(api)

    # Register the plugin to run at a priority slightly higher than NORMAL to help ensure that
    # the replacements are applied before most other metadata processing plugins are executed.
    api.register_track_metadata_processor(plugin.performer_tag_replace, priority=10)

    api.register_options_page(PerformerTagReplaceOptionsPage)


def migrate_settings(api: PluginApi):
    cfg = get_config()

    if cfg.setting.raw_value("performer_tag_replacement_pairs") is None or api.plugin_config["performer_tag_replacement_pairs"]:
        return

    api.logger.info("Migrating settings from 2.x version.")

    mapping = [
        ("performer_tag_replacement_pairs", str),
        ("performer_tag_replace_performers", bool),
    ]

    for key, qtype in mapping:
        if cfg.setting.raw_value(key) is None:
            api.logger.debug("No old setting for key: '%s'", key,)
            continue
        api.plugin_config[key] = cfg.setting.raw_value(key, qtype=qtype)
        cfg.setting.remove(key)
