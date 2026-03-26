from odoo.tests.common import TransactionCase

class TestModuloPrueba(TransactionCase):
    def test_01_verificacion_instalacion(self):
        # Este test solo verifica que el módulo está cargado
        module = self.env['ir.module.module'].search([('name', '=', 'modulo_prueba')])
        self.assertEqual(module.state, 'installed', "El módulo no se instaló correctamente")