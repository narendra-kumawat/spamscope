#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright 2016 Fedele Mantuano (https://www.linkedin.com/in/fmantuano/)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
import os
import unittest
from collections import deque

import mailparser

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from context import attachments, utils, DEFAULTS


MailAttachments = attachments.MailAttachments
write_payload = utils.write_payload
HashError = attachments.attachments.HashError
ContentTypeError = attachments.attachments.ContentTypeError

base_path = os.path.realpath(os.path.dirname(__file__))
mail = os.path.join(base_path, 'samples', 'mail_malformed_1')
mail_thug = os.path.join(base_path, 'samples', 'mail_thug')
mail_test_1 = os.path.join(base_path, 'samples', 'mail_test_1')
mail_test_2 = os.path.join(base_path, 'samples', 'mail_test_2')
mail_test_3 = os.path.join(base_path, 'samples', 'mail_test_3')
mail_test_8 = os.path.join(base_path, 'samples', 'mail_test_8')
mail_huge_archive = os.path.join(base_path, 'samples', 'mail_huge_archive')

OPTIONS = ChainMap(os.environ, DEFAULTS)

logging.getLogger().addHandler(logging.NullHandler())


class TestAttachments(unittest.TestCase):

    def setUp(self):
        # Init
        p = mailparser.parse_from_file(mail)
        self.attachments = p.attachments

        p = mailparser.parse_from_file(mail_thug)
        self.attachments_thug = p.attachments

        p = mailparser.parse_from_file(mail_test_1)
        self.attachments_test_1 = p.attachments

        p = mailparser.parse_from_file(mail_test_2)
        self.attachments_test_2 = p.attachments

        p = mailparser.parse_from_file(mail_test_3)
        self.attachments_test_3 = p.attachments

        p = mailparser.parse_from_file(mail_test_8)
        self.attachments_test_8 = p.attachments

        p = mailparser.parse_from_file(mail_huge_archive)
        self.attachments_huge_archive = p.attachments

    def test_not_extract_content_types(self):
        t = MailAttachments.withhashes(self.attachments_test_2)
        t(intelligence=False)
        self.assertIn("files", t[0])
        parameters = {
            "commons": {
                "not_extract_content_types": [
                    "application/java-archive", "application/x-rar"]}}

        t = MailAttachments.withhashes(self.attachments_test_2)
        t.reload(**parameters)
        t(intelligence=False)
        self.assertNotIn("files", t[0])

        t = MailAttachments.withhashes(self.attachments_test_8)
        t.reload(**parameters)
        t(intelligence=False)
        self.assertNotIn("files", t[0])

    def test_error_base64(self):
        t = MailAttachments.withhashes(self.attachments_test_1)
        t.run(intelligence=False)
        files = []

        for i in t:
            f = write_payload(i["payload"], i["extension"],
                              i["content_transfer_encoding"])
            files.append(f)

        for i in files:
            os.remove(i)

    def test_error_extract_rar(self):
        t = MailAttachments.withhashes(self.attachments_test_2)
        t.run(intelligence=False)
        self.assertEqual(len(t), 2)
        for i in t:
            self.assertEqual(i["Content-Type"], "application/x-rar")
            self.assertIn("files", i)

    def test_withhashes(self):
        t = MailAttachments.withhashes(self.attachments)
        self.assertIsInstance(t, MailAttachments)
        self.assertEqual(len(t), 1)

        for i in t:
            self.assertIn("md5", i)
            self.assertIn("sha1", i)
            self.assertIn("sha256", i)
            self.assertIn("sha512", i)
            self.assertIn("ssdeep", i)
            self.assertIn("filename", i)
            self.assertIn("payload", i)
            self.assertIn("mail_content_type", i)
            self.assertIn("content_transfer_encoding", i)

    def test_pophash(self):
        t = MailAttachments.withhashes(self.attachments)
        md5 = "1e38e543279912d98cbfdc7b275a415e"

        self.assertEqual(len(t), 1)

        with self.assertRaises(HashError):
            t.pophash("fake")

        t.pophash(md5)
        self.assertEqual(len(t), 0)

    def test_filter(self):
        t = MailAttachments.withhashes(self.attachments)
        check_list = deque(maxlen=10)
        md5 = "1e38e543279912d98cbfdc7b275a415e"

        check_list.append(md5)
        self.assertIn("payload", t[0])
        self.assertNotIn("is_filtered", t[0])

        r = t.filter(check_list, hash_type="md5")
        self.assertNotIn("payload", t[0])
        self.assertIn("is_filtered", t[0])
        self.assertEqual(True, t[0]["is_filtered"])
        self.assertIn(md5, r)

        check_list.extend(r)
        self.assertEqual(2, len(check_list))

        # It should not fail
        t.run(intelligence=False)

        t = MailAttachments.withhashes(self.attachments)
        check_list = deque(maxlen=10)
        md5 = "1e38e543279912d98cbfdc7b275a415f"
        check_list.append(md5)

        r = t.filter(check_list, hash_type="md5")
        self.assertIn("payload", t[0])
        self.assertIn("is_filtered", t[0])
        self.assertEqual(False, t[0]["is_filtered"])
        self.assertNotIn(md5, r)

    def test_run(self):
        t = MailAttachments.withhashes(self.attachments)
        t(intelligence=False)

        for i in t:
            self.assertIn("analisys_date", i)
            self.assertIn("extension", i)
            self.assertIn("size", i)
            self.assertIn("Content-Type", i)
            self.assertIn("is_archive", i)
            self.assertIn("files", i)

            self.assertEqual(i["extension"], ".zip")
            self.assertTrue(i["is_archive"])
            self.assertEqual(len(i["files"]), 1)

            for j in i["files"]:
                self.assertIn("analisys_date", j)
                self.assertIn("filename", j)
                self.assertIn("extension", j)
                self.assertIn("size", j)
                self.assertIn("Content-Type", j)
                self.assertIn("payload", j)
                self.assertIn("md5", j)

    def test_reload(self):
        dummy = {"key1": "value1", "key2": "value2"}
        t = MailAttachments.withhashes(self.attachments)
        t.reload(**dummy)
        self.assertEqual(t.key1, "value1")
        self.assertEqual(t.key2, "value2")
        self.assertEqual(len(t), 1)

        t(intelligence=False)
        t.removeall()
        self.assertEqual(len(t), 0)

    def test_filenamestext(self):
        t = MailAttachments.withhashes(self.attachments)
        t.run(intelligence=False)
        text = t.filenamestext()
        self.assertIsNotNone(text)
        self.assertNotIsInstance(text, list)
        self.assertNotIsInstance(text, dict)
        self.assertIn("20160523_916527.jpg_.zip", text)
        self.assertIn("20160523_211439.jpg_.jpg.exe", text)

    def test_payloadstext(self):
        t = MailAttachments.withhashes(self.attachments_thug)
        t.run(intelligence=False)
        text = t.payloadstext()
        self.assertIsNotNone(text)
        self.assertNotIsInstance(text, list)
        self.assertNotIsInstance(text, dict)
        self.assertIn("Windows", text)
        self.assertIn("setRequestHeader", text)

        check_list = deque(maxlen=10)
        md5 = "778cf2c48ab482d6134d4d12eb51192f"
        check_list.append(md5)
        self.assertIn("payload", t[0])
        self.assertNotIn("is_filtered", t[0])
        t.filter(check_list, hash_type="md5")
        self.assertNotIn("payload", t[0])
        text = t.payloadstext()
        self.assertFalse(text)

    def test_popcontenttype(self):
        t = MailAttachments.withhashes(self.attachments)
        t(intelligence=False)
        self.assertEqual(len(t), 1)
        t.popcontenttype("application/zip")
        self.assertEqual(len(t), 0)

        # Test path when attach is filtered
        t = MailAttachments.withhashes(self.attachments)
        t(intelligence=False)
        check_list = deque(maxlen=10)
        md5 = "1e38e543279912d98cbfdc7b275a415e"
        check_list.append(md5)
        t.filter(check_list, hash_type="md5")
        t.popcontenttype("application/zip")
        self.assertEqual(len(t), 0)

        t = MailAttachments.withhashes(self.attachments)
        t(intelligence=False)
        self.assertEqual(len(t[0]["files"]), 1)
        t.popcontenttype("application/x-dosexec")
        self.assertEqual(len(t[0]["files"]), 0)

        t = MailAttachments.withhashes(self.attachments)
        t(intelligence=False)
        t.popcontenttype("application/fake")
        self.assertEqual(len(t), 1)
        self.assertEqual(len(t[0]["files"]), 1)

        t = MailAttachments.withhashes(self.attachments)
        with self.assertRaises(ContentTypeError):
            t.popcontenttype("application/zip")

    def test_filtercontenttypes(self):
        t = MailAttachments.withhashes(self.attachments)

        parameters = {
            "commons": {
                "blacklist_content_types": [
                    "application/x-dosexec", "application/zip"]
            }
        }
        t.reload(**parameters)
        self.assertIn(
            "application/x-dosexec", t.commons["blacklist_content_types"])
        self.assertIn("application/zip", t.commons["blacklist_content_types"])

        self.assertEqual(len(t), 1)
        t(intelligence=False)
        self.assertEqual(len(t), 0)

        t.extend(self.attachments)
        parameters = {
            "commons": {
                "blacklist_content_types": ["application/x-dosexec"]
            }
        }
        t.reload(**parameters)
        t(intelligence=False)
        self.assertEqual(len(t), 1)
        self.assertEqual(len(t[0]["files"]), 0)

    @unittest.skipIf(
        OPTIONS["THUG_ENABLED"].capitalize() == "False" or OPTIONS[
            "VIRUSTOTAL_ENABLED"].capitalize() == "False",
        "Complete post processing test skipped: "
        "set env variables 'THUG_ENABLED', "
        "'VIRUSTOTAL_ENABLED' and 'ZEMANA_ENABLED' to True")
    def test_post_processing(self):
        t = MailAttachments.withhashes(self.attachments_thug)
        parameters = {
            "tika": {"enabled": True,
                     "path_jar": OPTIONS["TIKA_APP_JAR"],
                     "whitelist_content_types": ["application/zip"],
                     "memory_allocation": None},
            "virustotal": {"enabled": True,
                           "api_key": OPTIONS["VIRUSTOTAL_APIKEY"]},
            "thug": {"enabled": True,
                     "extensions": [".html", ".js", ".jse"],
                     "user_agents": ["win7ie90", "winxpie80"],
                     "referer": "http://www.google.com/",
                     "timeout": 300},
            "zemana": {"enabled": False,
                       "PartnerId": OPTIONS["ZEMANA_PARTNERID"],
                       "UserId": OPTIONS["ZEMANA_USERID"],
                       "ApiKey": OPTIONS["ZEMANA_APIKEY"],
                       "useragent": "SpamScope"}}

        t.reload(**parameters)
        t.run()
        for i in t:
            self.assertIn("tika", i)
            self.assertIn("virustotal", i)
            self.assertNotIn("zemana", i)
            self.assertNotIn("thug", i)

            for j in i.get("files", []):
                self.assertIn("virustotal", j)
                self.assertNotIn("zemana", j)
                self.assertIn("thug", j)

    def test_incorrect_padding(self):
        t = MailAttachments.withhashes(self.attachments_test_3)
        self.assertIsInstance(t, MailAttachments)
        self.assertEqual(len(t), 1)

        for i in t:
            self.assertIn("errors", i)
            self.assertIn("md5", i)
            self.assertIn("sha1", i)
            self.assertIn("sha256", i)
            self.assertIn("sha512", i)
            self.assertIn("ssdeep", i)
            self.assertIn("filename", i)
            self.assertIn("payload", i)
            self.assertIn("mail_content_type", i)
            self.assertIn("content_transfer_encoding", i)

    def test_filterforsize(self):
        parameters = {"commons": {
            "size.filter.enabled": True,
            "max.size": 3145728}}
        t = MailAttachments.withhashes(self.attachments_huge_archive)
        t.reload(**parameters)
        t(intelligence=False)
        self.assertNotIn("files", t[0])

        parameters = {"commons": {
            "size.filter.enabled": True,
            "max.size": 1024}}
        t = MailAttachments.withhashes(self.attachments_huge_archive)
        t.reload(**parameters)
        t(intelligence=False)
        self.assertNotIn("payload", t[0])

        parameters = {"commons": {
            "size.filter.enabled": True,
            "max.size": "1024"}}
        t = MailAttachments.withhashes(self.attachments_huge_archive)
        t.reload(**parameters)
        t(intelligence=False)
        self.assertNotIn("payload", t[0])

        parameters = {"commons": {
            "size.filter.enabled": False,
            "max.size": "1024"}}
        t = MailAttachments.withhashes(self.attachments_huge_archive)
        t.reload(**parameters)
        t(intelligence=False)
        self.assertIn("payload", t[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
