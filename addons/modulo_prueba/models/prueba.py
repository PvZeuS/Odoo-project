from odoo import models, fields

class ModeloPrueba(models.Model):
    _name = 'modulo.prueba'
    _description = 'Modelo de Prueba'

    name = fields.Char(string='Nombre de Prueba', required=True)  # Cambiado a False para permitir pruebas de campo requerido
    descripcion = fields.Text(string='Descripción')