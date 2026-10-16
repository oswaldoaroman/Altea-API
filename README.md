# Altea API

**Altea API** es el backend de Altea, una aplicación orientada a la prevención y concientización sobre el riesgo cardiovascular. Su propósito es conectar la aplicación con los servicios necesarios para gestionar usuarios, procesar información y proporcionar funcionalidades de asistencia mediante inteligencia artificial.

## ¿Qué es?

Altea API es un servicio desarrollado en Python con FastAPI que centraliza la lógica del servidor y permite la comunicación entre la aplicación cliente y los componentes del sistema.

Forma parte de una solución que busca ayudar a los usuarios a comprender los factores asociados al riesgo cardiovascular, recibir recomendaciones informativas y resolver dudas mediante un asistente conversacional.

## ¿Cómo funciona?

La API recibe solicitudes de la aplicación cliente, valida los datos proporcionados y los dirige al componente responsable de procesarlos. Para ello, organiza sus responsabilidades en diferentes módulos:

- **Routers:** definen los endpoints y gestionan las solicitudes HTTP y las conexiones disponibles.
- **Schemas:** establecen la estructura y validación de los datos de entrada y salida.
- **Models:** representan las entidades y estructuras de datos utilizadas por el sistema.
- **Database:** agrupa los componentes relacionados con el acceso y la configuración de la base de datos.
- **Services:** contienen la lógica de negocio y coordinan las operaciones necesarias para atender las solicitudes.
- **Autenticación y seguridad:** utilizan mecanismos basados en JWT para gestionar el acceso a los recursos protegidos.
- **Integración con inteligencia artificial:** permite conectar el backend con Ollama para proporcionar asistencia conversacional.

Esta organización permite que cada componente tenga una responsabilidad definida y facilita la comunicación entre las distintas partes del sistema.

## ¿Por qué se utiliza esta arquitectura?

La separación entre rutas, validación, acceso a datos y lógica de negocio busca reducir el acoplamiento entre componentes, facilitar las pruebas y permitir que las funcionalidades evolucionen sin afectar innecesariamente al resto del sistema.

FastAPI proporciona una estructura eficiente para construir servicios web y definir interfaces de comunicación. La validación de datos ayuda a mantener la consistencia de la información recibida, mientras que JWT permite implementar mecanismos de autenticación para los recursos que lo requieren.

Por su parte, la integración con inteligencia artificial amplía las capacidades de Altea al permitir interacciones conversacionales, manteniendo esta funcionalidad dentro de una arquitectura de servicios diferenciados.

## Objetivo

Altea API busca proporcionar una base modular, mantenible y extensible para el desarrollo de Altea, facilitando la integración de sus funcionalidades de gestión de usuarios, evaluación cardiovascular y asistencia informativa.

El proyecto se encuentra en desarrollo y evoluciona conforme se incorporan y validan nuevas funcionalidades.

## Consideraciones sobre salud

Altea tiene un enfoque preventivo y educativo. La información generada por el sistema no sustituye el diagnóstico, la valoración ni el tratamiento de un profesional de la salud.

---

**Altea — Tecnología orientada a la prevención y concientización sobre la salud cardiovascular.**
