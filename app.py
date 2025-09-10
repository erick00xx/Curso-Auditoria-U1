from openai import OpenAI
from flask import Flask, send_from_directory, request, jsonify, Response
import re

app = Flask(__name__)

# Ruta para servir el index.html desde la carpeta dist
@app.route('/',  methods=["GET",'POST'])
def serve_index():
    return send_from_directory('dist', 'index.html')

# Ruta para servir los archivos estáticos generados
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('dist', path)

client = OpenAI(
    base_url = 'http://localhost:11434/v1',
    api_key='ollama', # requerido, pero no utilizado
)

@app.route('/analizar-riesgos', methods=['POST'])
def analizar_riesgos():
    data = request.get_json()  # Obtener datos JSON enviados al endpoint
    activo = data.get('activo')  # Extraer el valor del activo
    if not activo:
        return jsonify({"error": "El campo 'activo' es necesario"}), 400
    
    riesgos, impactos = obtener_riesgos(activo)  # Llamar a la función mejorada
    return jsonify({"activo": activo, "riesgos": riesgos, "impactos": impactos})

@app.route('/sugerir-tratamiento', methods=['POST'])
def sugerir_tratamiento():
    data = request.get_json()  # Obtener datos JSON enviados al endpoint
    activo = data.get('activo')  # Extraer el valor del activo
    riesgo = data.get('riesgo')  # Extraer el valor del riesgo
    impacto = data.get('impacto')  # Extraer el valor del impacto

    if not activo or not riesgo or not impacto:
        return jsonify({"error": "Los campos 'activo', 'riesgo' e 'impacto' son necesarios"}), 400

    # Combinar la información para darle más contexto a la IA
    entrada_tratamiento = f"Activo: {activo}; Riesgo: {riesgo}; Impacto: {impacto}"
    tratamiento = obtener_tratamiento(entrada_tratamiento)
    
    return jsonify({"activo": activo, "riesgo": riesgo, "impacto": impacto, "tratamiento": tratamiento})


def obtener_tratamiento(riesgo_info):
    response = client.chat.completions.create(
        model="llama3",
        messages=[
            {"role": "system", "content": "Eres un auditor de ciberseguridad experto en ISO 27001 para el sector bancario. Basado en el activo, riesgo e impacto proporcionados, sugiere una recomendación o control de mitigación específico y accionable. Si es posible, referencia un control del Anexo A de la ISO 27001. Tu respuesta debe ser concisa, profesional y no exceder los 250 caracteres."},
            {"role": "user", "content": "Activo: Servidor de Base de Datos; Riesgo: Fuga de datos; Impacto: Exposición de información financiera y personal de miles de clientes, resultando en multas regulatorias y daño reputacional masivo."},
            {"role": "assistant",  "content": "Implementar cifrado a nivel de base de datos (TDE) y en tránsito (TLS). Aplicar el principio de mínimo privilegio en las cuentas de acceso, acorde al control A.9.2.3 de ISO 27001."},
            {"role": "user", "content": riesgo_info }
        ]
    )
    answer = response.choices[0].message.content
    return answer

def obtener_riesgos(activo):
    response = client.chat.completions.create(
        model="llama3",
        messages=[
            {"role": "system", "content": "Eres un auditor de ciberseguridad experto en el sector bancario y la norma ISO 27001. Para el activo de información proporcionado, identifica 5 riesgos de seguridad críticos y distintos. Describe el riesgo y su impacto potencial en el banco. Debes formatear cada uno estrictamente así, sin texto introductorio: '**Nombre del Riesgo**: Descripción detallada del impacto.'"},
            {"role": "user", "content": "Aplicación Web de Banca"},
            {"role": "assistant",  "content": """**Inyección SQL (SQLi)**: Un atacante podría explotar vulnerabilidades para manipular la base de datos subyacente, permitiendo el acceso, modificación o eliminación de datos sensibles de clientes, como saldos y transacciones.
**Fallo en el Control de Acceso**: Usuarios no autorizados podrían acceder a funcionalidades o datos restringidos, como ver las cuentas de otros clientes o realizar operaciones no permitidas para su perfil.
**Configuración de Seguridad Incorrecta**: Errores en la configuración del servidor web, como servicios innecesarios expuestos o mensajes de error detallados, podrían revelar información sensible del sistema y facilitar ataques.
**Cross-Site Scripting (XSS)**: Permite a un atacante inyectar scripts maliciosos que se ejecutan en el navegador de otros usuarios, facilitando el robo de sesiones, credenciales y la suplantación de identidad.
**Uso de Componentes con Vulnerabilidades Conocidas**: La utilización de librerías o frameworks de terceros desactualizados puede exponer la aplicación a vulnerabilidades ya descubiertas y explotables públicamente."""},
            {"role": "user", "content": activo }
        ]
    )
    answer = response.choices[0].message.content
    
    # Patrón de Regex mejorado para capturar correctamente el riesgo y el impacto.
    patron = r'\*\*(.*?)\*\*:\s*(.*?)(?=\n\*\*|\Z)'
    
    # Buscamos todos los patrones en la respuesta, permitiendo que el impacto ocupe múltiples líneas (re.DOTALL)
    resultados = re.findall(patron, answer, re.DOTALL)
    
    # Si el regex falla, intentamos un método más simple como fallback.
    if not resultados:
        riesgos = []
        impactos = []
        lines = answer.split('\n')
        for line in lines:
            if '**:' in line:
                parts = line.split('**:', 1)
                riesgo = parts[0].replace('**', '').replace('•','').strip()
                impacto = parts[1].strip()
                if riesgo and impacto:
                    riesgos.append(riesgo)
                    impactos.append(impacto)
        return riesgos, impactos

    # Separamos los resultados en dos listas: riesgos e impactos
    riesgos = [resultado[0].strip() for resultado in resultados]
    impactos = [resultado[1].strip() for resultado in resultados]
    
    return riesgos, impactos

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port="5500")