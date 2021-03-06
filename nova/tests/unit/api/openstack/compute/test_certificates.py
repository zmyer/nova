# Copyright (c) 2012 OpenStack Foundation
# All Rights Reserved.
# Copyright 2013 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
from oslo_policy import policy as oslo_policy
from webob import exc

from nova.api.openstack.compute import certificates \
        as certificates_v21
from nova.cert import rpcapi
from nova import context
from nova import exception
from nova import policy
from nova import test
from nova.tests.unit.api.openstack import fakes


class CertificatesTestV21(test.NoDBTestCase):
    certificates = certificates_v21
    url = '/v2/fake/os-certificates'
    certificate_show_extension = 'os_compute_api:os-certificates:show'
    certificate_create_extension = \
        'os_compute_api:os-certificates:create'

    def setUp(self):
        super(CertificatesTestV21, self).setUp()
        self.context = context.RequestContext('fake', 'fake')
        self.controller = self.certificates.CertificatesController()
        self.req = fakes.HTTPRequest.blank('')

    def test_translate_certificate_view(self):
        pk, cert = 'fakepk', 'fakecert'
        view = self.certificates._translate_certificate_view(cert, pk)
        self.assertEqual(view['data'], cert)
        self.assertEqual(view['private_key'], pk)

    @mock.patch.object(rpcapi.CertAPI, 'fetch_ca', return_value='fakeroot')
    def test_certificates_show_root(self, mock_fetch_ca):
        res_dict = self.controller.show(self.req, 'root')

        response = {'certificate': {'data': 'fakeroot', 'private_key': None}}
        self.assertEqual(res_dict, response)
        mock_fetch_ca.assert_called_once_with(mock.ANY, project_id='fake')

    def test_certificates_show_policy_failed(self):
        rules = {
            self.certificate_show_extension: "!"
        }
        policy.set_rules(oslo_policy.Rules.from_dict(rules))
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.show, self.req, 'root')
        self.assertIn(self.certificate_show_extension,
                      exc.format_message())

    @mock.patch.object(rpcapi.CertAPI, 'generate_x509_cert',
                       return_value=('fakepk', 'fakecert'))
    def test_certificates_create_certificate(self, mock_generate_x509_cert):
        res_dict = self.controller.create(self.req)

        response = {
            'certificate': {'data': 'fakecert',
                            'private_key': 'fakepk'}
        }
        self.assertEqual(res_dict, response)
        mock_generate_x509_cert.assert_called_once_with(mock.ANY,
                                                        user_id='fake_user',
                                                        project_id='fake')

    def test_certificates_create_policy_failed(self):
        rules = {
            self.certificate_create_extension: "!"
        }
        policy.set_rules(oslo_policy.Rules.from_dict(rules))
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.create, self.req)
        self.assertIn(self.certificate_create_extension,
                      exc.format_message())

    @mock.patch.object(rpcapi.CertAPI, 'fetch_ca',
                side_effect=exception.CryptoCAFileNotFound(project='fake'))
    def test_non_exist_certificates_show(self, mock_fetch_ca):
        self.assertRaises(
            exc.HTTPNotFound,
            self.controller.show,
            self.req, 'root')
