from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestModeloPrueba(TransactionCase):

    def setUp(self):
        """Preparamos los datos básicos para las pruebas"""
        super(TestModeloPrueba, self).setUp()
        # Creamos un registro base para usar en los tests
        self.registro_base = self.env['modulo.prueba'].create({
            'name': 'Test Inicial',
            'descripcion': 'Una descripción de prueba'
        })

    def test_01_creacion_correcta(self):
        """Este test va a fallar porque la comparación será falsa"""
        # Cambiamos 'Test Inicial' por algo que NO existe
        self.assertEqual(self.registro_base.name, 'Este nombre causara error')

    def test_02_campo_requerido(self):
        """Verifica que el sistema lance error si falta el nombre (required=True)"""
        with self.assertRaises(Exception): # Odoo lanzará una excepción de integridad SQL
            self.env['modulo.prueba'].create({
                'name': False,  # Esto debería fallar
                'descripcion': 'Sin nombre'
            })

    def test_03_cambio_valor(self):
        """Verifica que se pueden actualizar los registros"""
        self.registro_base.write({'name': 'Nombre Editado'})
        self.assertEqual(self.registro_base.name, 'Nombre Editado')