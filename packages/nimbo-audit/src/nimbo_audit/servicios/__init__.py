"""Servicios del CLI.

Piezas de lógica reutilizable, inyectables en los comandos: hashing SHA-256 de
evidencia (`hashing`, RF-03/2B), render Markdown del reporte (`reporte`, RF-04/2C)
y exportación opcional a PDF vía pandoc (`pdf`, RF-04/2C). El registro de sesión
(RF-02) llegará en un paso posterior.
"""
