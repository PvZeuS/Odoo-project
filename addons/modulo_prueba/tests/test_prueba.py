from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo.tests import tagged

@tagged('post_install', '-at_install', '/modulo_prueba')
class TestModeloPrueba(TransactionCase):

    def setUp(self):
        """Datos iniciales para las pruebas"""
        super(TestModeloPrueba, self).setUp()
        # Creamos un registro base
        self.registro = self.env['modulo.prueba'].create({
            'name': 'Test Inicial',
            'descripcion': 'Descripción de prueba'
        })

    def test_01_creacion_valida(self):
        """Validar que los datos se guardan correctamente"""
        self.assertEqual(self.registro.name, 'Test Inicial')
        self.assertEqual(self.registro.descripcion, 'Descripción de prueba')

    def test_02_error_nombre_vacio(self):
        """Validar que falle si no hay nombre (required=True)"""
        # Intentar crear un registro sin nombre debe lanzar una excepción
        with self.assertRaises(Exception): 
            self.env['modulo.prueba'].create({
                'name': False,
                'descripcion': 'Esto no debería guardarse'
            })

    def test_03_actualizacion(self):
        """Validar que el registro se puede editar"""
        self.registro.write({'name': 'Nombre Editado'})
        self.assertEqual(self.registro.name, 'Nombre Editado')