# Bitácora de Troubleshooting - Cuentas-Casa Build

Este archivo contiene los errores encontrados durante el desarrollo del APK y sus soluciones definitivas.

## 2026-01-27: Fallo en el Bundling de Metro (Módulos no encontrados)
- **Error:** `Metro has encountered an error: Cannot find module './src/theme/colors'`
- **Causa:** La carpeta `src` estaba presente pero sus archivos interiores habían desaparecido o no fueron creados correctamente.
- **Solución:** Recrear manualmente los archivos `src/theme/colors.ts`, `src/api/types.ts` y `src/api/client.ts`.
- **Verificación:** Ejecutar el comando de bundling manual especificado en `text file.txt`.

## 2026-01-27: Error de Plugins de Gradle (expo-module-gradle-plugin)
- **Error:** `Plugin [id: 'expo-module-gradle-plugin'] was not found`
- **Causa:** El `prebuild` se realizó sin tener las dependencias de Expo sincronizadas, por lo que el scaffolding de Android no incluyó los plugins necesarios.
- **Solución:** 
  1. Correr `npx expo install --fix` para sincronizar versiones.
  2. Borrar carpeta `android`.
  3. Ejecutar `npx expo prebuild --platform android --no-install`.

## 2026-01-27: Recursos Bloqueados (EBUSY)
- **Error:** `EBUSY: resource busy or locked, unlink ...` al intentar borrar la carpeta `android`.
- **Causa:** Procesos de Java (Gradle Daemon) manteniendo bloqueados los archivos de la caché.
- **Solución:** Ejecutar `taskkill /F /IM java.exe /T` en PowerShell/CMD para forzar el cierre.

## 2026-01-27: Problemas de Rutas con Espacios (Windows)
- **Error:** Fallos aleatorios en Gradle al buscar el compilador de Java.
- **Causa:** `JAVA_HOME` apuntando a `C:\Program Files\...` (el espacio rompe algunos scripts de Gradle).
- **Solución:** Usar la ruta corta 8.3: `C:\PROGRA~1\Android\ANDROI~1\jbr`. Confirmar con `dir /x C:\`.

---
*Este documento se actualizará en cada iteración de build.*
