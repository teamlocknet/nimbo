# ADR-000 — Codename y nombre del proyecto

**Estado:** Aceptado

## Contexto

El proyecto de grado del grupo LockNet es un sistema operativo de ciberseguridad
basado en Debian cuyo **nombre real aún no está decidido**. Necesitamos empezar a
construir el monorepo (repos, paquetes, comandos, namespaces) sin bloquearnos por
esa decisión pendiente, y sin tener que reescribir medio proyecto cuando el nombre
se defina. Entre los candidatos heredados figuran **VELDORA** y **NEXUS**.

## Decisión

Se adopta **`nimbo`** como **codename desechable** y **slug canónico único** en todo
el proyecto: nombres de repositorio, paquetes, comandos, namespaces y rutas. La
convención es **un solo slug (`nimbo`) en todas partes**, de modo que el día que se
decida el nombre real se adopte con **un único find-and-replace global**. `nimbo` es
prestado: no se le atribuye valor de marca y no debe aparecer razonamiento que
dependa de su significado.

El nombre real queda **pendiente**; su elección se registrará en un ADR posterior
que reemplazará o complementará a este.

## Consecuencias

- El rename futuro es una operación mecánica de find-and-replace sobre un único
  token, en lugar de una migración manual dispersa.
- Todo el código y la documentación nueva deben usar `nimbo` como slug, nunca un
  nombre alternativo, para preservar la propiedad del find-and-replace único.
- Se evita el bikeshedding del nombre ahora; la decisión de marca se difiere sin
  frenar la ingeniería.
- Cuando se decida el nombre real, este ADR quedará como registro histórico del
  porqué del codename.

## Fecha

2026-09-03
