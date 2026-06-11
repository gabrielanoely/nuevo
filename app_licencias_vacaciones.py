import csv
import os
from datetime import datetime, date

# ============================================================
# CONFIGURACIÓN DE ARCHIVOS GABI
# ============================================================

ARCHIVO_EMPLEADOS = "datos/empleados.csv"
ARCHIVO_SOLICITUDES = "datos/solicitudes.csv"

# IMPORTANTE:
# Estos campos deben coincidir con las columnas reales de los CSV.
# Si falta un campo en esta lista, al reescribir el archivo se puede perder esa columna.
CAMPOS_EMPLEADOS = [
    "legajo",
    "nombre",
    "apellido",
    "sector",
    "dias_disponibles",
    "estado"
]

CAMPOS_SOLICITUDES = [
    "id_solicitud",
    "legajo",
    "sector",
    "fecha_inicio",
    "fecha_fin",
    "dias_solicitados",
    "estado",
    "motivo_rechazo"
]


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def pausar():
    input("\nPresione enter para continuar...")


def crear_carpeta_datos():
    """
    Crea la carpeta datos si no existe.
    Esto evita errores al guardar los archivos CSV.
    """
    if not os.path.exists("datos"):
        os.makedirs("datos")


def fila_es_cabecera_repetida(fila, campos):
    """
    Detecta filas que por error quedaron guardadas como si fueran datos,
    pero en realidad son la cabecera del archivo CSV.
    """
    for campo in campos:
        if fila.get(campo, "") != campo:
            return False

    return True


def preparar_fila(fila, campos):
    """
    Prepara una fila leída del CSV para que tenga todos los campos esperados.

    Esto sirve para evitar errores si un archivo anterior no tenía alguna columna,
    por ejemplo motivo_rechazo en solicitudes.csv.
    """
    fila_preparada = {}

    for campo in campos:
        valor = fila.get(campo, "")

        if valor is None:
            valor = ""

        fila_preparada[campo] = valor.strip()

    return fila_preparada


# ============================================================
# LECTURA Y ESCRITURA DE CSV
# ============================================================

def leer_csv_como_diccionario(ruta, campos, campo_clave):
    """
    Lee un CSV y lo guarda en un diccionario.

    La clave del diccionario será:
    - empleados.csv: legajo
    - solicitudes.csv: id_solicitud
    """
    datos = {}

    try:
        if not os.path.exists(ruta):
            return datos

        with open(ruta, "r", encoding="utf-8-sig", newline="") as archivo:
            lector = csv.DictReader(archivo)

            for fila in lector:
                fila = preparar_fila(fila, campos)

                if not fila_es_cabecera_repetida(fila, campos):
                    clave = fila.get(campo_clave, "").strip()

                    if clave != "":
                        datos[clave] = fila

    except Exception as error:
        print(f"ERROR al leer el archivo {ruta}: {error}")

    return datos


def guardar_diccionario_en_csv(ruta, datos, campos):
    """
    Guarda un diccionario completo en un archivo CSV.

    Se reescribe todo el archivo, pero se conservan todos los registros
    que están guardados en el diccionario.
    """
    crear_carpeta_datos()
    ruta_temporal = ruta + ".tmp"

    try:
        with open(ruta_temporal, "w", encoding="utf-8", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=campos, extrasaction="ignore")
            escritor.writeheader()

            for clave in datos:
                escritor.writerow(datos[clave])

        os.replace(ruta_temporal, ruta)
        return True

    except Exception as error:
        print(f"ERROR al guardar el archivo {ruta}: {error}")

        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)

        return False


def cargar_base_de_datos():
    """
    Carga los dos CSV en un único diccionario de datos.
    """
    base_datos = {
        "empleados": leer_csv_como_diccionario(
            ARCHIVO_EMPLEADOS,
            CAMPOS_EMPLEADOS,
            "legajo"
        ),
        "solicitudes": leer_csv_como_diccionario(
            ARCHIVO_SOLICITUDES,
            CAMPOS_SOLICITUDES,
            "id_solicitud"
        )
    }

    return base_datos


def guardar_base_de_datos(base_datos):
    """
    Guarda empleados.csv y solicitudes.csv desde el diccionario de datos.
    """
    empleados_guardados = guardar_diccionario_en_csv(
        ARCHIVO_EMPLEADOS,
        base_datos["empleados"],
        CAMPOS_EMPLEADOS
    )

    solicitudes_guardadas = guardar_diccionario_en_csv(
        ARCHIVO_SOLICITUDES,
        base_datos["solicitudes"],
        CAMPOS_SOLICITUDES
    )

    return empleados_guardados and solicitudes_guardadas


# ============================================================
# VALIDACIONES DE EMPLEADO
# ============================================================

def buscar_empleado(base_datos, legajo):
    return base_datos["empleados"].get(legajo)


def empleado_activo(empleado):
    return empleado.get("estado", "").upper() == "ACTIVO"


def convertir_entero(valor):
    try:
        return int(valor)
    except ValueError:
        return 0


def saldo_suficiente(empleado, dias_solicitados):
    dias_disponibles = convertir_entero(empleado.get("dias_disponibles", "0"))
    return dias_solicitados <= dias_disponibles


# ============================================================
# VALIDACIONES DE FECHAS
# ============================================================

def convertir_fecha(texto_fecha):
    try:
        return datetime.strptime(texto_fecha, "%Y-%m-%d").date()
    except ValueError:
        return None


def fecha_tiene_formato_valido(texto_fecha):
    """
    Valida que la fecha ingresada tenga formato AAAA-MM-DD.
    No registra rechazos: solo controla la carga correcta del dato.
    """
    return convertir_fecha(texto_fecha) is not None


def fecha_no_es_pasada(fecha):
    """
    Valida que la fecha de inicio no sea anterior al día actual.
    Esto se trata como un error de carga, no como rechazo de negocio.
    """
    return fecha >= date.today()


def calcular_dias_solicitados(fecha_inicio, fecha_fin):
    diferencia = fecha_fin - fecha_inicio
    return diferencia.days + 1


def fechas_superpuestas(inicio_1, fin_1, inicio_2, fin_2):
    """
    Devuelve True si dos rangos de fechas se pisan entre sí.
    """
    return inicio_1 <= fin_2 and fin_1 >= inicio_2


# ============================================================
# VALIDACIÓN DE SUPERPOSICIÓN POR SECTOR
# ============================================================

def existe_superposicion_sector(base_datos, empleado_actual, fecha_inicio, fecha_fin):
    sector_actual = empleado_actual.get("sector")
    legajo_actual = empleado_actual.get("legajo")

    for id_solicitud in base_datos["solicitudes"]:
        solicitud = base_datos["solicitudes"][id_solicitud]

        if solicitud.get("estado", "").upper() == "APROBADA":
            legajo_solicitud = solicitud.get("legajo")

            if legajo_solicitud != legajo_actual:
                empleado_solicitud = buscar_empleado(base_datos, legajo_solicitud)

                if empleado_solicitud is not None:
                    mismo_sector = empleado_solicitud.get("sector") == sector_actual

                    if mismo_sector:
                        inicio_existente = convertir_fecha(solicitud.get("fecha_inicio", ""))
                        fin_existente = convertir_fecha(solicitud.get("fecha_fin", ""))

                        if inicio_existente is not None and fin_existente is not None:
                            if fechas_superpuestas(fecha_inicio, fecha_fin, inicio_existente, fin_existente):
                                return True

    return False


def existe_superposicion_empleado(base_datos, empleado_actual, fecha_inicio, fecha_fin):
    """
    Valida que el mismo empleado no tenga ya una solicitud APROBADA
    en el mismo rango de fechas o en un rango que se superponga.

    Ejemplo:
    - Solicitud existente: 2026-07-15 al 2026-07-20
    - Nueva solicitud:      2026-07-15 al 2026-07-15

    En ese caso devuelve True, porque el empleado ya tiene aprobada esa fecha.
    """
    legajo_actual = empleado_actual.get("legajo")

    for id_solicitud in base_datos["solicitudes"]:
        solicitud = base_datos["solicitudes"][id_solicitud]

        misma_persona = solicitud.get("legajo") == legajo_actual
        solicitud_aprobada = solicitud.get("estado", "").upper() == "APROBADA"

        if misma_persona and solicitud_aprobada:
            inicio_existente = convertir_fecha(solicitud.get("fecha_inicio", ""))
            fin_existente = convertir_fecha(solicitud.get("fecha_fin", ""))

            if inicio_existente is not None and fin_existente is not None:
                if fechas_superpuestas(fecha_inicio, fecha_fin, inicio_existente, fin_existente):
                    return True

    return False


# ============================================================
# SOLICITUDES
# ============================================================

def obtener_proximo_id(base_datos):
    mayor_id = 0

    for id_solicitud in base_datos["solicitudes"]:
        try:
            id_actual = int(id_solicitud)

            if id_actual > mayor_id:
                mayor_id = id_actual

        except ValueError:
            pass

    return str(mayor_id + 1)


def formatear_fecha_para_csv(fecha, texto_original):
    """
    Si la fecha fue convertida correctamente, se guarda con formato AAAA-MM-DD.
    Si no se pudo convertir, se guarda el texto original ingresado por el usuario.
    """
    if fecha is not None:
        return fecha.strftime("%Y-%m-%d")

    return texto_original


def crear_solicitud(
    base_datos,
    empleado,
    texto_inicio,
    texto_fin,
    fecha_inicio,
    fecha_fin,
    dias_solicitados,
    estado,
    motivo_rechazo
):
    id_nuevo = obtener_proximo_id(base_datos)

    nueva_solicitud = {
        "id_solicitud": id_nuevo,
        "legajo": empleado.get("legajo"),
        "sector": empleado.get("sector"),
        "fecha_inicio": formatear_fecha_para_csv(fecha_inicio, texto_inicio),
        "fecha_fin": formatear_fecha_para_csv(fecha_fin, texto_fin),
        "dias_solicitados": str(dias_solicitados),
        "estado": estado,
        "motivo_rechazo": motivo_rechazo
    }

    return id_nuevo, nueva_solicitud


def registrar_solicitud(base_datos, nueva_solicitud):
    """
    Guarda una solicitud en el diccionario de datos, ya sea APROBADA o RECHAZADA.
    """
    id_solicitud = nueva_solicitud.get("id_solicitud")
    base_datos["solicitudes"][id_solicitud] = nueva_solicitud


def registrar_solicitud_rechazada(
    base_datos,
    empleado,
    texto_inicio,
    texto_fin,
    fecha_inicio,
    fecha_fin,
    dias_solicitados,
    motivo_rechazo
):
    """
    Registra una solicitud rechazada en solicitudes.csv.

    No descuenta días al empleado porque la solicitud no fue aprobada.
    """
    id_nuevo, nueva_solicitud = crear_solicitud(
        base_datos,
        empleado,
        texto_inicio,
        texto_fin,
        fecha_inicio,
        fecha_fin,
        dias_solicitados,
        "RECHAZADA",
        motivo_rechazo
    )

    registrar_solicitud(base_datos, nueva_solicitud)
    datos_guardados = guardar_base_de_datos(base_datos)

    if datos_guardados:
        pass
    else:
        print("La solicitud fue rechazada, pero ocurrió un error al guardar los archivos.")


def descontar_dias_empleado(empleado, dias_solicitados):
    saldo_actual = convertir_entero(empleado.get("dias_disponibles", "0"))
    nuevo_saldo = saldo_actual - dias_solicitados
    empleado["dias_disponibles"] = str(nuevo_saldo)


# ============================================================
# PANTALLAS / MENÚS
# ============================================================

def mostrar_bienvenida():
    print("=" * 60)
    print("CHATBOT DE GESTIÓN DE VACACIONES")
    print("=" * 60)
    print("Este sistema permite consultar saldo y generar solicitudes.")
    print("Las fechas deben ingresarse con formato AAAA-MM-DD.")
    print("Ejemplo: 2026-07-15")
    print("=" * 60)


def menu_inicial():
    print("\nMENÚ INICIAL")
    print("1. Ingresar legajo")
    print("2. Salir")
    return input("Seleccione una opción: ").strip()


def menu_principal(nombre):
    print(f"\nMENÚ PRINCIPAL - Usuario: {nombre}")
    print("1. Consultar saldo")
    print("2. Generar solicitud")
    print("3. Salir")
    return input("Seleccione una opción: ").strip()


def solicitar_legajo(base_datos):
    print("\nVALIDACIÓN DE LEGAJO")
    legajo = input("Ingrese su legajo: ").strip()

    empleado = buscar_empleado(base_datos, legajo)

    if empleado is None:
        print("\nLegajo inválido o inexistente.")
        pausar()
        return None

    if not empleado_activo(empleado):
        print("\nEl empleado se encuentra inactivo. No puede solicitar vacaciones.")
        pausar()
        return None

    print(f"\nLegajo validado correctamente.\nTe damos la bienvenida, {empleado.get('nombre')}!")
    pausar()
    return empleado


def consultar_saldo(empleado):
    print("\nCONSULTA DE SALDO")
    print(f" * Empleado/a: {empleado.get('nombre')} {empleado.get('apellido')}")
    print(f" * Sector: {empleado.get('sector')}")
    print(f" * Días disponibles: {empleado.get('dias_disponibles')}")
    pausar()


def pedir_fecha_inicio():
    """
    Solicita la fecha de inicio y la valida en el momento.

    Si el usuario escribe mal el formato, no se registra una solicitud rechazada.
    Se le pide que ingrese nuevamente la fecha porque todavía es un error de carga.
    """
    while True:
        texto_inicio = input("Fecha inicio: ").strip()
        fecha_inicio = convertir_fecha(texto_inicio)

        if fecha_inicio is None:
            print("Fecha ingresada incorrecta. Debe usar el formato AAAA-MM-DD. Intente nuevamente.")

        elif not fecha_no_es_pasada(fecha_inicio):
            print("La fecha de inicio no puede ser una fecha pasada. Intente nuevamente.")

        else:
            return texto_inicio, fecha_inicio


def pedir_fecha_fin(fecha_inicio):
    """
    Solicita la fecha de fin y la valida en el momento.

    También se controla que no sea anterior a la fecha de inicio.
    Si hay error, se vuelve a pedir la fecha final.
    """
    while True:
        texto_fin = input("Fecha fin: ").strip()
        fecha_fin = convertir_fecha(texto_fin)

        if fecha_fin is None:
            print("Fecha ingresada incorrecta. Debe usar el formato AAAA-MM-DD. Intente nuevamente.")

        elif fecha_fin < fecha_inicio:
            print("La fecha de fin no puede ser anterior a la fecha de inicio. Intente nuevamente.")

        else:
            return texto_fin, fecha_fin


def pedir_fechas_validas():
    """
    Pide las fechas ya validadas.

    En este punto no se rechaza ninguna solicitud por formato, fecha pasada
    u orden incorrecto. Esos casos se consideran errores de carga y se corrigen
    antes de continuar con las reglas de negocio.
    """
    print("\nGENERAR SOLICITUD")
    print("Ingrese las fechas con formato AAAA-MM-DD.")
    print("Ejemplo: 2026-07-15")

    texto_inicio, fecha_inicio = pedir_fecha_inicio()
    texto_fin, fecha_fin = pedir_fecha_fin(fecha_inicio)

    return texto_inicio, texto_fin, fecha_inicio, fecha_fin


# ============================================================
# FLUJO PRINCIPAL DE GENERACIÓN DE SOLICITUD
# ============================================================

def generar_solicitud(base_datos, empleado):
    dias_disponibles = convertir_entero(empleado.get("dias_disponibles", "0"))

    if dias_disponibles <= 0:
        motivo_rechazo = "Falta de días disponibles."

        print("\nSolicitud rechazada.")
        print(f"Motivo: {motivo_rechazo}")
        print("El empleado no cuenta con días disponibles para solicitar vacaciones.")

        registrar_solicitud_rechazada(
            base_datos,
            empleado,
            "",
            "",
            None,
            None,
            0,
            motivo_rechazo
        )

        pausar()
        return

    texto_inicio, texto_fin, fecha_inicio, fecha_fin = pedir_fechas_validas()

    dias_solicitados = calcular_dias_solicitados(fecha_inicio, fecha_fin)

    if not saldo_suficiente(empleado, dias_solicitados):
        motivo_rechazo = "Saldo insuficiente."

        print("\nSolicitud rechazada.")
        print(f"Motivo: {motivo_rechazo}")
        print(f"Días solicitados: {dias_solicitados}")
        print(f"Días disponibles: {empleado.get('dias_disponibles')}")

        registrar_solicitud_rechazada(
            base_datos,
            empleado,
            texto_inicio,
            texto_fin,
            fecha_inicio,
            fecha_fin,
            dias_solicitados,
            motivo_rechazo
        )

        pausar()
        return

    if existe_superposicion_empleado(base_datos, empleado, fecha_inicio, fecha_fin):
        motivo_rechazo = "El empleado ya tiene una solicitud aprobada en esas fechas."

        print("\nSolicitud rechazada.")
        print(f"Motivo: {motivo_rechazo}")

        registrar_solicitud_rechazada(
            base_datos,
            empleado,
            texto_inicio,
            texto_fin,
            fecha_inicio,
            fecha_fin,
            dias_solicitados,
            motivo_rechazo
        )

        pausar()
        return

    if existe_superposicion_sector(base_datos, empleado, fecha_inicio, fecha_fin):
        motivo_rechazo = "Conflicto de cobertura del sector."

        print("\nSolicitud rechazada.")
        print(f"Motivo: {motivo_rechazo}")
        print("Ya existe otro empleado del mismo sector con vacaciones aprobadas en esas fechas.")

        registrar_solicitud_rechazada(
            base_datos,
            empleado,
            texto_inicio,
            texto_fin,
            fecha_inicio,
            fecha_fin,
            dias_solicitados,
            motivo_rechazo
        )

        pausar()
        return

    id_nuevo, nueva_solicitud = crear_solicitud(
        base_datos,
        empleado,
        texto_inicio,
        texto_fin,
        fecha_inicio,
        fecha_fin,
        dias_solicitados,
        "APROBADA",
        ""
    )

    # Primero se modifica la información en el diccionario de datos.
    registrar_solicitud(base_datos, nueva_solicitud)
    descontar_dias_empleado(empleado, dias_solicitados)

    # Después se guarda nuevamente el contenido completo de los CSV.
    datos_guardados = guardar_base_de_datos(base_datos)

    if datos_guardados:
        print("\nSOLICITUD APROBADA")
        print(f"Días solicitados: {dias_solicitados}")
        print(f"Nuevo saldo disponible: {empleado.get('dias_disponibles')}")
        print("La solicitud fue registrada correctamente!")
    else:
        print("\nLa solicitud fue procesada, pero ocurrió un error al guardar los archivos.")
        print("Revise los archivos CSV antes de continuar.")

    pausar()


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    base_datos = cargar_base_de_datos()

    if len(base_datos["empleados"]) == 0:
        print("Error: no hay empleados cargados. Comunicate con RRHH para más información.")
        return

    mostrar_bienvenida()

    sistema_activo = True
    empleado_validado = None

    while sistema_activo:
        if empleado_validado is None:
            opcion = menu_inicial()

            if opcion == "1":
                empleado_validado = solicitar_legajo(base_datos)

            elif opcion == "2":
                print("\nGracias por utilizar el chatbot. Hasta luego!")
                sistema_activo = False

            else:
                print("\nOpción inválida. Intente nuevamente.")
                pausar()

        else:
            opcion = menu_principal(empleado_validado.get("nombre"))

            if opcion == "1":
                consultar_saldo(empleado_validado)

            elif opcion == "2":
                generar_solicitud(base_datos, empleado_validado)

            elif opcion == "3":
                print("\nGracias por utilizar el chatbot. Hasta luego!")
                sistema_activo = False

            else:
                print("\nOpción inválida. Intente nuevamente.")
                pausar()


if __name__ == "__main__":
    main()
