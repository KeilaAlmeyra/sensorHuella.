import time
import sys
from pyfingerprint.pyfingerprint import PyFingerprint
from mfrc522 import MFRC522
import RPi.GPIO as GPIO
import smbus2
from RPLCD.i2c import CharLCD

# Dirección I2C del PCF8574A (puede variar, verifica con i2cdetect)
I2C_ADDRESS = 0x3F  # Cambia a 0x27 si usas PCF8574 en lugar de PCF8574A
I2C_PORT = 1  # Generalmente 1 en Raspberry Pi

# Configuración del LCD
lcd = CharLCD(
    i2c_expander='PCF8574',
    address=I2C_ADDRESS,
    port=I2C_PORT,
    cols=16,  # Número de columnas del LCD
    rows=2,   # Número de filas del LCD
    charmap='A00',
    auto_linebreaks=False
)

def mostrar_contador_regresivo():
    for i in range(3, 0, -1):
        lcd.cursor_pos = (1, 0)
        lcd.write_string(f"Confirma en: {i} ")
        lcd.cursor_pos = (1,15)
        lcd.write_string(str(i))
        time.sleep(1)

    lcd.cursor_pos = (1,0)
    lcd.write_string("Ejecutando...")
    time.sleep(2)
    lcd.clear()
lcd.clear()
# inicializar el sensor

try:
    sensor = PyFingerprint('/dev/serial0', 57600, 0xFFFFFFFF, 0x00000000)
    if not sensor.verifyPassword():
        raise ValueError('Contrasena incorrecta')
except Exception as e:
    print('Error al inicializar el sensor')
    sys.exit(1)
    

# ----------------------------------------------------
lector = MFRC522()
LLAVERO_ADMIN = 860664956428

# estados
reseteo = 1
bandera = 0
intentos = 3
salir = 0
# -------------------------

def detectar_toque(sensor):
    while not sensor.readImage():
        time.sleep(0.05)
    start = time.time()
    
    while sensor.readImage():
        time.sleep(0.05)
    duration = time.time() - start
    return duration


def detectar_doble_toque(sensor, maximo = 0.5, timeout=5.0):
    tiempo_inicio= time.time()
    
    while time.time() - tiempo_inicio < timeout:
        if sensor.readImage():
            while sensor.readImage():
                time.sleep(0.02)
            inicio_segundo = time.time()
            while time.time() - inicio_segundo < maximo:
                if sensor.readImage():
                    while sensor.readImage():
                        time.sleep(0.02)
                    return True
                time.sleep(0.01)
            return False
        time.sleep(0.01)
    return False

def enroll_finger(sensor):
    try:
        print('Coloca tu dedo en el sensor')
        while not sensor.readImage():
            pass
        sensor.convertImage(1)
        result = sensor.searchTemplate()
        posicion = result[0]
        
        if posicion >= 0:
            print(f'Huella ya registrada en el ID {posicion}')
            return
        
        print('Retire su dedo')
        time.sleep(2)
        
        print('Colocar mismo dedo')
        while not sensor.readImage():
            pass
        sensor.convertImage(2)
        
        if sensor.compareCharacteristics==0:
            print('Huella no coincide. Reintentar')
            return
        
        sensor.createTemplate()
        posicion= sensor.storeTemplate()
        print(f'Huella registrada correctamente en el ID {posicion}')
    
    except Exception as e:
        print('Error durante el registro')
        print(str(e))


def borrar_huella(sensor):
    try:
        total = sensor.getTemplateCount()
        if total==0:
            print('No hay huellas registradas')
            return
        print(f'Cantidad de huellas registradas: {total}')
        
 
        huella_aBorrar = int(input('Ingresar ID huella a borrar'))
        
        if sensor.deleteTemplate(huella_aBorrar):
            print('Huella eliminada correctamente')
        else:
            print('No se pudo eliminar la huella')
        
    except Exception as e:
        print('Error al eliminar huella', e)

def mostrar_buscar(sensor):
    try:
        total = sensor.getTemplateCount()
        capacidad = sensor.getStorageCapacity()

        if total ==0:
            print(f'No hay huellas registradas.')
            return
        
        else: 
            print(f'Huellas registradas: {total} ')
            print('Coloca tu dedo en el sensor para buscar...')
            
            while not sensor.readImage():
                pass

            sensor.convertImage(1)

            result = sensor.searchTemplate()
            positionNumber = result[0]

            if positionNumber >= 0:
                print(f'La huella ya está registrada en la posición #{positionNumber}.')
                return

            else:
                print('No se encontró ninguna huella coincidente.')

    except Exception as e:
        print('Error inesperado')

def verificar_huella():
    global intentos, bandera
    print('Coloque su huella')
    
    while intentos > 0 and bandera == 0:
        try:
            if sensor.readImage():
                sensor.convertImage(1)
                result = sensor.searchTemplate()
                if result[0] == -1:
                    print('Huella no identificada. Reintentar')
                    intentos = intentos -1
                else:
                    print('Huella verificada. Bienvenido.')
                    bandera = 1
                    return True
        except Exception as e:
            print('Error en la lectura. Reintentar')
            intentos = intentos -1
    return False

def verificar_llavero():
    global bandera, intentos
    print('Inserte llave RFID')
    start= time.time()
    
    while time.time() - start < 10:
        (status, TagType) = lector.MFRC522_Request(lector.PICC_REQIDL)
        if status == lector.MI_OK:
            (status, uid) = lector.MFRC522_Anticoll()
            if status == lector.MI_OK:
                identificador = int.from_bytes(bytearray(uid), byteorder="little")
                if identificador == LLAVERO_ADMIN:
                    print('Llave correcta')
                    bandera = 1
                    return True
            else:
                print('Llave incorrecta. Reintentar')
                intentos = intentos -1
                return False
                
    print('No se detecto llave valida')
    intentos = intentos -1
    return False

def sacar_dedo(sensor):
    print('Retire el dedo')
    while sensor.readImage():
        time.sleep(0.5)


def menu():
    global salir
    opciones = ['Registrar Huella', 'Mostrar/Buscar huella', 'Eliminar Huella', 'Salir.']
    current = 0
    
    while salir == 0:
        print(f'\n {opciones[current]} ?')
        duration = detectar_toque(sensor)
        
        if duration >= 3.0:
            mostrar_contador_regresivo()
            print(f'Opcion seleccionada: {opciones[current]}')
            if current == 0:
                enroll_finger(sensor)
            elif current == 1:
                mostrar_buscar(sensor)
            elif current == 2:
                borrar_huella(sensor)
            elif current == 3:
                print('Saliendo del menu...')
                salir = 1
            sacar_dedo(sensor)
        else:
            current = (current + 1) % len(opciones)

while reseteo == 1:
    print('Inicializando...\n')
    time.sleep(3.0)
    if detectar_doble_toque(sensor):
        if verificar_llavero():
            print('Abriendo Menu administrador...')
            menu()
            reseteo = 0
        else:
            if intentos == 0:
                print('Demasiados intentos. Bloqueando sistema...')
                time.sleep(1800)
                intentos = 3
    
    else:
        if verificar_huella():
            print('Sistema desbloqueado.')
            reseteo = 0
        else:
            if intentos == 0 and  bandera == 0:
                print('Demasiados intentos fallidos. Inserte llave RFID')
                if verificar_llavero():
                    print('Sistema desbloqueado.')
                    reseteo = 0
                else:
                    if intentos == 0:
                        print('Sistema bloqueado.')
                        time.sleep(1800)
                        intentos = 3
