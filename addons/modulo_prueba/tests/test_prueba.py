from odoo.tests.common import TransactionCase

class TestModuloPrueba(TransactionCase):
    def test_01_verificacion_modelo(self):
        # Verificamos que el modelo existe en el registro de Odoo
        #self.assertIn('modulo.prueba', self.env, "El modelo 'modulo.prueba' no se registró correctamente")
        # Si antes tenías self.assertEqual(1, 1)
        self.assertEqual(1, 2, "Error provocado: 1 no es 2")