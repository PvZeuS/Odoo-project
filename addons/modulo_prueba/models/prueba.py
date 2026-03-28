from odoo import models, fields

class ModeloPrueba(models.Model):
    _name = 'modulo.prueba'
    _description = 'Modelo de Prueba'

    name = fields.Char(string='Nombre de Prueba', required=False)  
    descripcion = fields.Text(string='Descripción')