import time
import statistics
from hx711 import HX711

# Parámetros
DOUT, PD_SCK    = 20, 21
PESO_REF_G      = 1000.0
MUESTRAS        = 200     # lee 30 muestras y luego filtra
RECORTE_PCT     = 0.10   # elimina el 10% más alto y el 10% más bajo

def leer_filtrado(hx, muestras, recorte_pct):
    """Lee `muestras` raw, ordena y descarta recorte_pct de valores extremos."""
    vals = []
    for _ in range(muestras):
        # forzar canal A/128
        hx.power_up()
        time.sleep(0.01)
        vals.append(hx.get_raw_data(times=2)[0])
        hx.power_down()
    vals.sort()
    k = int(len(vals) * recorte_pct)
    central = vals[k:len(vals)-k]
    return statistics.mean(central)

def calibrar():
    hx = HX711(DOUT, PD_SCK)
    time.sleep(0.1)

    # 1) Offset (célula vacía)
    print("Midiendo offset (sin peso)…")
    offset = leer_filtrado(hx, MUESTRAS, RECORTE_PCT)
    print(f"  Offset filtrado: {offset:.2f}")

    input(f"\n→ Coloca {PESO_REF_G:.0f} g y ENTER…")

    # 2) Lectura con peso de referencia
    print("Midiendo raw con peso de referencia…")
    raw_ref = leer_filtrado(hx, MUESTRAS, RECORTE_PCT)
    print(f"  Raw con peso: {raw_ref:.2f}")

    # 3) Cálculo del scale
    diff  = raw_ref - offset
    scale = diff / PESO_REF_G
    print(f"\n  Diff = {diff:.2f} → scale = {scale:.4f} raw/g")

    print("\n¡Calibración lista! Usa estos valores:")
    print(f"OFFSET = {offset:.2f}")
    print(f"SCALE  = {scale:.4f}")

    return offset, scale

if __name__ == "__main__":
    calibrar()
