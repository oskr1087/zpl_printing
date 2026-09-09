# PLS ZPL Labels - Odoo 19

Módulo de etiquetas PLS integrado con QZ Tray.

## Dependencias
- `qz_tray_base`
- `qz_tray_report`
- `stock`
- `sale_stock`

## Etiquetas
1. **Bulto Parcial 4x2**: ZPL monocromo.
2. **Ubicación 4x6**: QWeb PDF a color para impresión mediante QZ Tray.
   - Pasillo: azul.
   - Columna: verde.
   - Nivel: naranja.
   - Posición: morado.
   - El nombre se forma automáticamente con esos cuatro campos.
3. **Trazabilidad del Pedido 4x3**: ZPL monocromo.

La etiqueta de ubicación no utiliza ZPL puro porque ZPL en impresoras térmicas Zebra convencionales es monocromático. Para preservar color se genera un PDF 4x6 y se envía por el flujo de impresión de QZ Tray.
