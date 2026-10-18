// Descarga de archivos en el navegador (Semana 18): el blob llega de
// la API y se guarda con un enlace temporal. Compartido por la página
// de Reportes y por el botón de exportar de la bitácora.
export function guardarArchivo(archivo, nombre) {
  const url = URL.createObjectURL(archivo)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
