# Maquetador de Cartas
## Guía de ayuda

## ¿Para qué sirve este programa?

Existen herramientas excelentes para preparar juegos **Print & Play**. Algunas, como **PNP Tools**, **PrintPlay Studio**, **PnP PDF Creator** o **P&P Cards Layout de Boardssey**, pueden coger tus imágenes de cartas y colocarlas sobre páginas A4 o US Letter para generar un PDF preparado para imprimir.

Estas herramientas resuelven muy bien el problema de la **maquetación de las hojas de impresión**.

Este programa resuelve un problema anterior:

> **Si quieres que tus imágenes de cartas estén ya preparadas con el tamaño exacto que debe tener cada carta, este es tu programa.**

Su función es preparar las imágenes individuales para que puedas llevarlas después a tu programa de maquetación o impresión habitual.

El programa se ocupa de:

- la proporción de la carta;
- el recorte;
- el número exacto de píxeles de salida;
- los PPP/PPI como información de impresión;
- ampliaciones o reducciones cuando son necesarias;
- y el perfil ICC de la imagen, cuando existe.

Después puedes utilizar las imágenes resultantes en cualquier herramienta de maquetación, diseño o impresión.

---

# 1. Píxeles, tamaño físico y PPP son cosas distintas

Esta es la parte que más confunde.

Para entender cómo se imprime una imagen hay que separar tres conceptos:

### Píxeles

Los píxeles son el **tamaño de la imagen digital**.

Por ejemplo:

`750 × 1050 píxeles`

significa que la imagen tiene 750 píxeles de ancho y 1050 de alto.

Esos píxeles contienen la información de la imagen.

### Tamaño físico

Es lo que queremos que mida la carta sobre el papel.

Por ejemplo:

`6,35 × 8,89 cm`

### PPP / PPI

En imágenes digitales suele hablarse de **PPI** (pixels per inch), aunque muchos programas muestran **DPI**.

Este valor relaciona los píxeles con el tamaño físico de impresión.

No crea detalle.

---

# 2. El ejemplo que lo aclara todo

Supongamos que queremos una carta de:

`6,35 × 8,89 cm`

Eso son:

`2,5 × 3,5 pulgadas`

Si queremos imprimirla a 300 PPI:

- `2,5 × 300 = 750 píxeles`
- `3,5 × 300 = 1050 píxeles`

Por eso una carta de ese tamaño puede prepararse como:

**750 × 1050 px a 300 PPI**

La combinación es coherente:

**750 × 1050 píxeles → 6,35 × 8,89 cm a 300 PPI**

---

# 3. Cambiar los PPP no crea más detalle

Este es el error más habitual.

Imaginemos que tenemos:

`750 × 1050 píxeles`

y cambiamos únicamente el valor de 300 PPI a 150 PPI.

La imagen sigue teniendo:

`750 × 1050 píxeles`

No hemos añadido información.

No hay más detalle.

Solo estamos diciendo que esos mismos píxeles deben ocupar un tamaño físico diferente.

Por eso:

> **Cambiar de 72 a 300 PPI no convierte una imagen pequeña en una imagen de alta resolución.**

Si una imagen tiene 500 × 700 píxeles, escribir "300 PPI" en sus metadatos no hace que de repente tenga calidad equivalente a una imagen de 1500 × 2100 píxeles.

Los píxeles son los que contienen el detalle.

---

# 4. Entonces, ¿para qué sirven los PPP?

Porque necesitamos relacionar la imagen digital con el tamaño físico final.

Por ejemplo:

`750 × 1050 px @ 300 PPI`

significa que esos 750 × 1050 píxeles se imprimirán a 300 píxeles por pulgada.

El resultado físico es:

`2,5 × 3,5 pulgadas`

es decir:

`6,35 × 8,89 cm`

Por eso usamos los PPP como parte de la preparación del archivo.

La forma correcta de pensarlo es:

**1. ¿Qué tamaño físico quiero?**  
**2. ¿Cuántos píxeles quiero tener para ese tamaño?**  
**3. ¿Qué valor de PPI relaciona ambos?**

No al revés.

---

# 5. El tamaño en píxeles es lo realmente importante

Para preparar una carta, el dato fundamental es que el archivo tenga los píxeles necesarios para el tamaño final.

Por ejemplo, si el destino es:

`750 × 1050 px`

eso es lo que determina la cantidad de detalle disponible en la imagen final.

Los PPI son importantes para que un programa de impresión sepa cómo relacionar esos píxeles con el tamaño físico.

Una buena analogía es esta:

> **Los píxeles son la cantidad de información que tienes. Los PPI indican cómo se reparte esa información sobre el papel.**

Cambiar la etiqueta de PPI no crea información nueva.

---

# 6. ¿Qué pasa si la imagen original tiene más resolución?

Perfecto.

Supongamos que el recorte que necesitamos tiene:

`1500 × 2100 píxeles`

y nuestra carta final necesita:

`750 × 1050 píxeles`

Tenemos el doble de resolución.

El programa reduce la imagen a:

`750 × 1050`

utilizando **LANCZOS**, un método de redimensionado de alta calidad.

---

# 7. ¿Qué pasa si la imagen tiene exactamente la resolución necesaria?

No hacemos nada.

Por ejemplo:

```text
Canvas recortado:
750 × 1050 px

Salida:
750 × 1050 px
```

La imagen ya tiene exactamente los píxeles necesarios.

El programa:

- no redimensiona;
- no aplica enfoque;
- no altera innecesariamente los píxeles.

Es el caso ideal.

---

# 8. ¿Y si la imagen tiene menos resolución?

Por ejemplo:

```text
Canvas recortado:
600 × 840 px

Salida:
750 × 1050 px
```

Necesitamos ampliar.

En estos casos el programa utiliza:

**LANCZOS + una máscara de enfoque muy suave**

El enfoque es deliberadamente conservador.

No queremos crear halos alrededor de letras, iconos, líneas o marcos.

En una carta esos artefactos son especialmente visibles. Por eso la ampliación está pensada para **casos pequeños y residuales**, no como sustituto de una herramienta de superresolución.

Si una imagen necesita una ampliación importante, es preferible tratarla previamente con una herramienta como **Upscayl** y volver a introducir el resultado en este flujo.

---

# 9. El cálculo se hace después del recorte

Esto es importante.

No comparamos la resolución de la fotografía original con la resolución final.

Primero determinamos el recorte necesario para obtener la proporción de la carta.

Por ejemplo:

```text
Foto original
4000 × 3000
        ↓
recorte para obtener la proporción de la carta
        ↓
Canvas útil
2100 × 2800
        ↓
comparación con el destino
        ↓
Salida
750 × 1050
```

La resolución que importa es la del **canvas resultante del recorte**, porque esa es la parte de la imagen que realmente vamos a conservar.

Es posible tener una fotografía enorme que, después de recortar, tenga menos resolución útil de la que parece.

---

# 10. Reducir, no tocar o ampliar

La aplicación distingue tres casos:

### Canvas mayor que la salida

Se reduce con **LANCZOS**.

### Canvas exactamente igual que la salida

No se hace ningún resize.

### Canvas menor que la salida

Se amplía con **LANCZOS + enfoque muy suave**.

La finalidad es evitar procesado innecesario y mantener la imagen lo más limpia posible.

---

# 11. El programa no sustituye a un maquetador PDF

Nuestro programa prepara:

**las imágenes individuales**

Otras herramientas preparan:

**la hoja de impresión**

Por ejemplo:

```text
Fotos originales
      ↓
Maquetador de Cartas
      ↓
Imágenes exactas de las cartas
      ↓
PNP Tools / PrintPlay Studio / PnP PDF Creator / etc.
      ↓
PDF A4 / Letter
      ↓
Impresión
```

La ventaja es que la imagen ya entra en el siguiente programa con la proporción y los píxeles correctos.

---

# 12. Cómo imprimir después

Cuando imprimas las cartas o generes el PDF final, evita que el programa vuelva a escalarlas automáticamente.

Cuando exista la opción, busca:

- **100 %**
- **Tamaño real**
- **Actual Size**
- **Sin escala**

Y evita opciones como:

- **Ajustar a página**
- **Fit to page**
- **Encajar**
- **Reducir / ampliar automáticamente**

Si el programa vuelve a escalar la imagen, el tamaño físico final puede cambiar.

---

# 13. Sangrado: la imagen debe traerlo ya incorporado

El sangrado es una extensión de la imagen que queda fuera del tamaño final de corte. Muchas imprentas trabajan con **3 mm de sangrado por cada lado**, aunque debes seguir siempre las especificaciones de tu imprenta.

Nuestro programa **no crea ni añade el sangrado**. Solo permite trabajar con imágenes que ya lo contienen. Al activar esta opción, el programa interpreta que la imagen de entrada incluye ese margen adicional y calcula el canvas completo en consecuencia.

Por ejemplo, una carta de:

`63,5 × 88,9 mm`

con 3 mm de sangrado por cada lado debe llegar al programa como una imagen de:

`69,5 × 94,9 mm`

El tamaño físico de corte sigue siendo:

`63,5 × 88,9 mm`

y los 3 mm adicionales de cada lado quedan fuera del área de corte.

## ¿Por qué es importante configurarlo bien?

Es un error tratar una imagen que ya mide `69,5 × 94,9 mm` como si fuera una carta Standard de `63,5 × 88,9 mm` **sin sangrado**. En ese caso estaríamos diciendo al programa que todo el archivo corresponde al tamaño de corte, cuando en realidad contiene 3 mm adicionales alrededor.

En el programa, la opción se muestra como:

**La imagen incluye sangrado**

Está desactivada por defecto. Si se activa, el valor inicial es **3 mm por lado**, y puede cambiarse por otro valor si la imprenta lo requiere.

El cálculo pasa a ser:

```text
Tamaño de corte
      +
Sangrado izquierdo + derecho
      +
Sangrado superior + inferior
      ↓
Canvas completo de la imagen
```

La preview muestra la línea de corte para que puedas distinguir visualmente el tamaño de la carta del área de sangrado.

El sangrado también se tiene en cuenta al calcular la resolución y al decidir si el canvas necesita reducción, ampliación o ningún redimensionado.

Si utilizas después una herramienta de maquetación como PNP Tools, revisa cómo interpreta exactamente su configuración de sangrado y sigue sus indicaciones.

# 14. Espacio de color e ICC

Los PPP y el espacio de color son problemas diferentes.

El espacio de color describe **cómo deben interpretarse los valores de color de la imagen**.

Algunos ejemplos son:

- sRGB
- Adobe RGB
- otros espacios definidos mediante perfiles ICC

## ¿Qué hace el programa?

El programa **conserva el perfil ICC incrustado en la imagen de entrada**, cuando existe.

Por tanto:

```text
sRGB → sRGB
Adobe RGB → Adobe RGB
otro ICC → mismo ICC
```

No convertimos automáticamente Adobe RGB a sRGB.

Tampoco convertimos automáticamente a CMYK.

Esto es deliberado.

Queremos evitar una conversión de color innecesaria y conservar la información de color que traía el archivo.

## ¿Por qué es importante?

Los mismos valores RGB pueden representar colores diferentes según el espacio de color.

El perfil ICC permite que otro programa sepa cómo interpretar correctamente esos valores.

Por eso una imagen Adobe RGB no debería quedarse sin su perfil y después ser interpretada como sRGB por otro programa.

## ¿Y qué perfil debo usar para imprimir?

Depende del destino.

Una imprenta puede trabajar con:

- sRGB;
- Adobe RGB;
- un perfil CMYK concreto;
- un perfil ICC propio;
- o unas instrucciones específicas.

**Sigue siempre las especificaciones de la imprenta antes de convertir el archivo.**

Nuestro programa no hace esa conversión automáticamente: conserva el perfil de entrada.

## ¿Y si la imagen no tiene perfil?

No inventamos uno.

Si el archivo no contiene un perfil ICC incrustado, la salida tampoco recibe uno artificialmente.

En un flujo profesional conviene saber con qué espacio de color se creó originalmente la imagen antes de realizar una conversión.

---

# 15. El informe del ZIP

Cada tanda incluye un archivo:

`INFORME.txt`

El informe permite comprobar cómo se ha preparado cada imagen.

Puede indicar:

- proyecto;
- tamaño de carta;
- resolución de salida;
- desplazamiento del recorte;
- tamaño del canvas utilizado;
- operación realizada;
- perfil ICC detectado.

Además se incluye un aviso cuando corresponde recordar que la imprenta puede exigir un perfil concreto.

---

# 16. Resumen

Si solo quieres recordar unas pocas cosas:

### Los píxeles contienen el detalle

`750 × 1050 px` significa que la imagen tiene 750 × 1050 píxeles reales.

### Los PPI relacionan esos píxeles con el papel

`750 × 1050 px @ 300 PPI` corresponde a una carta de `6,35 × 8,89 cm`.

### Cambiar los PPI no crea detalle

Pasar una imagen de 150 a 300 PPI sin aumentar sus píxeles **no mejora su resolución real**.

### El programa mira la resolución después del recorte

Es el canvas final el que determina si hace falta reducir, no hacer nada o ampliar.

### El color también importa

El programa conserva el perfil ICC de entrada cuando existe. La conversión a otro perfil debe hacerse de acuerdo con las especificaciones de la imprenta o del flujo de trabajo final.

### Al imprimir, evita una segunda escala

Si el archivo ya está preparado al tamaño correcto, usa **100 % / tamaño real** salvo que el flujo de trabajo indique otra cosa.

---

## En una frase

> **Este programa prepara tus imágenes para que salgan con la proporción correcta, el tamaño exacto en píxeles, los PPI adecuados y su perfil de color conservado, listas para entrar en tu herramienta de maquetación o impresión.**
