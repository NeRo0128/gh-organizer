# demo.tape - Script de grabación para gh-organizer
Output docs/assets/demo.gif

# Configuración de la terminal
Set FontSize 20
Set Width 1200
Set Height 800
Set Padding 20
Set Margin 20
Set MarginFill "#1e1e2e"
Set BorderRadius 10
Set Theme "Catppuccin Mocha"
Set FontFamily "JetBrainsMono Nerd Font"
Set Shell "fish"

# Ocultar el prompt de la shell antes de empezar
Hide
Type "clear"
Enter
Show

# 1. Iniciar la app (esperar a que carguen los repositorios)
Type "gh-organizer"
Enter
Sleep 15s
# 2. Navegar por el árbol
Down
Down
Down
Sleep 1s

# 3. Probar la búsqueda (Filtro)
Type "/"
Sleep 500ms
Type "web"
Sleep 2s
Escape
Sleep 1s

# 4. Auto-organizar
Type "o"
Sleep 1s
Down
Enter
Sleep 3s

# 5. Crear una nueva colección
Type "n"
Sleep 1s
Type "Trabajo/Clientes"
Sleep 500ms
Enter
Sleep 2s

# 6. Seleccionar un repo y ver los commits
Down
Down
Sleep 3s

# 7. Salir de la app
Type "q"
Sleep 2s
