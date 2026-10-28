# Verificación matemática de la simulación

Este documento explica **cómo comprobar que la simulación resuelve correctamente
su modelo matemático**, con cálculos que se pueden hacer a mano y pruebas que se
ejecutan con un comando.

> **Verificación ≠ validación.** *Verificar* es demostrar que el programa
> resuelve bien las ecuaciones planteadas. *Validar* es demostrar que esas
> ecuaciones representan bien un acueducto real (requiere datos de campo).
> Aquí se hace la verificación.

## 0. Cómo ejecutarla

```bash
uv run python -m regulador.verificacion   # informe con esperado / obtenido / error
uv run pytest                             # las mismas comprobaciones + pruebas unitarias
```

Resultado actual (Python 3.12, valores nominales):

| # | Comprobación | Esperado | Obtenido | Error |
|---|---|---:|---:|---:|
| 1 | Vaciado libre vs. solución exacta | 3.519631056 m | 3.519631056 m | 1.3e-15 |
| 2 | Orden de convergencia RK4 | 4 | 4.009 | 9.5e-03 |
| 3 | Equilibrio AUTO, C = 0.018 | 4.000000 m | 4.000000 m | 1.1e-11 |
| 4 | Equilibrio AUTO, C = 0.030 | 3.811898 m | 3.811898 m | 4.5e-12 |
| 5 | Equilibrio MANUAL | 4.000000 m | 4.000000 m | 1.1e-10 |
| 6 | Decaimiento lineal en t = τ | 0.367879 | 0.367882 | 2.6e-06 |
| 7 | Balance de volumen con 19 eventos | 1.519770 m³ | 1.519770 m³ | 1.1e-09 |
| 8 | Eventos: Δt = 0.05 vs. referencia 0.001 | 3.911446986 m | 3.911446986 m | 2.1e-10 |
| 9 | Reproducibilidad con semilla | 0 | 0 | 0 |
| 10 | Media entre llegadas | 12.0405 s | 12.0464 s | 5.9e-03 |
| 11 | Demanda media (Ley de Little) | 13.95 L/s | 13.81 L/s | 1.0 % |

---

## 1. Modelo que se verifica

$$\frac{dh}{dt} = g(h,t) = \frac{Q_{in}(h) - C\sqrt{h} - D(t)}{A}$$

$$Q_{in}^{AUTO} = \mathrm{sat}_{[0,\,Q_{max}]}\!\left[Q_b + K_p(h_{ref}-h)\right],\qquad Q_b = C_{nom}\sqrt{h_{ref}}$$

Valores nominales: $A=3$, $C=C_{nom}=0.018$, $K_p=0.12$, $Q_{max}=0.09$,
$Q_{manual}=0.036$, $h_{ref}=4$. Código: `regulador/model.py`.

---

## 2. Prueba 1 — Solución analítica exacta (vaciado libre)

Con la bomba apagada y sin consumidores ($Q_{in}=0$, $D=0$):

$$\frac{dh}{dt} = -\frac{C}{A}\sqrt{h}$$

Cambio de variable $u=\sqrt{h}$: $\;\dfrac{du}{dt} = \dfrac{1}{2\sqrt h}\dfrac{dh}{dt} = -\dfrac{C}{2A}$,
que es constante. Integrando:

$$\boxed{h(t) = \left(\sqrt{h_0} - \frac{C\,t}{2A}\right)^2}\qquad (t \le 2A\sqrt{h_0}/C)$$

**Cálculo a mano** ($h_0=5$ m, $t=120$ s):

$$\sqrt5 = 2.236068,\quad \frac{0.018\cdot120}{2\cdot3} = 0.36,\quad h = (1.876068)^2 = 3.519631\ \text{m}$$

El simulador da 3.519631056 m (error $10^{-15}$, precisión de máquina).
Esto prueba que la ecuación $Q_{out}=C\sqrt h$, la división por $A$ y el
integrador están bien implementados.

## 3. Prueba 2 — Orden de convergencia de Runge–Kutta 4

RK4 tiene error global $e(\Delta t) \approx K\,\Delta t^4$. Si se reduce el paso
a la mitad, el error debe dividirse por $2^4 = 16$. El **orden observado** es:

$$p = \log_2 \frac{e(\Delta t)}{e(\Delta t/2)}$$

Usando el problema de la Prueba 1 (solución exacta conocida):

| Δt (s) | Error | Cociente | p |
|---:|---:|---:|---:|
| 8 | 6.77e-10 | — | — |
| 4 | 4.21e-11 | 16.1 | 4.01 |
| 2 | 2.63e-12 | 16.0 | 4.00 |
| 1 | 1.62e-13 | 16.2 | 4.02 |

$p \approx 4$ confirma que el método implementado es realmente RK4 de cuarto
orden (un error en los coeficientes $1/6, 2/6, 2/6, 1/6$ lo bajaría a 1 o 2).

## 4. Pruebas 3, 4 y 5 — Equilibrios analíticos

En equilibrio $dh/dt = 0$. Sin demanda y sin saturar la bomba:

$$Q_b + K_p(h_{ref} - h^*) = C\sqrt{h^*}$$

Con $x = \sqrt{h^*}$ queda una cuadrática:

$$K_p x^2 + C x - (Q_b + K_p h_{ref}) = 0 \;\Rightarrow\;
\boxed{h^* = \left(\frac{-C + \sqrt{C^2 + 4K_p(Q_b + K_p h_{ref})}}{2K_p}\right)^2}$$

Como $K_p>0$ y $Q_b + K_p h_{ref} > 0$, el producto de raíces es negativo: hay
**una sola** raíz positiva.

**Caso nominal ($C = 0.018$).** $Q_b = 0.018\sqrt4 = 0.036$.

$$0.12x^2 + 0.018x - 0.516 = 0,\quad \Delta = 0.000324 + 0.24768 = 0.248004,\quad \sqrt\Delta = 0.498$$
$$x = \frac{-0.018 + 0.498}{0.24} = 2 \;\Rightarrow\; h^* = 4.000\ \text{m}$$

**Caso $C = 0.030$** ($Q_b$ sigue siendo 0.036 porque usa $C_{nom}$):

$$0.12x^2 + 0.030x - 0.516 = 0,\quad \sqrt{0.24858} = 0.498578,\quad x = 1.952408 \;\Rightarrow\; h^* = 3.8119\ \text{m}$$

El nivel queda **por debajo** de 4 m: es el error estacionario típico de un
regulador solo proporcional cuando la planta real difiere de la nominal.

**Comprobación de no saturación:** en $h^*$, $Q_{in} = Q_{out} = C\sqrt{h^*}$:
0.036 m³/s y 0.0586 m³/s respectivamente, ambos dentro de $[0, 0.09]$. ✔

**MANUAL:** $Q_{manual} = C\sqrt{h^*} \Rightarrow h^* = (0.036/0.018)^2 = 4.000$ m.

La prueba integra desde $h_0 = 3.35$ m durante mucho más que $5\tau$ y compara.
Error $\sim10^{-11}$ m.

## 5. Prueba 6 — Estabilidad y constante de tiempo

Sea $g(h) = \dfrac{Q_b + K_p(h_{ref}-h) - C\sqrt h}{A}$. Derivando:

$$g'(h) = -\frac{1}{A}\left(K_p + \frac{C}{2\sqrt h}\right) < 0 \quad \forall h>0$$

- Como $g$ es **estrictamente decreciente**, el equilibrio es único y
  **globalmente estable** (para una EDO escalar autónoma: si $h > h^*$ entonces
  $dh/dt < 0$ y viceversa).
- Linealizando, una perturbación pequeña $\delta$ evoluciona como
  $\delta(t) = \delta\,e^{-t/\tau}$ con

$$\tau = \frac{A}{K_p + C/(2\sqrt{h^*})} = \frac{3}{0.12 + 0.018/4} = \frac{3}{0.1245} = 24.10\ \text{s}$$

En MANUAL desaparece $K_p$: $\tau = 3/0.0045 = 666.7$ s (el regulador acelera
la respuesta ≈ 28 veces).

**Prueba:** se arranca en $h^* + 0.005$ m y se integra durante $\tau$. Debe
quedar $\delta/e$, es decir el cociente $0.367879$. Se obtiene $0.367882$
(la diferencia $2.6\times10^{-6}$ es el término no lineal, que desaparece al
reducir $\delta$).

## 6. Prueba 7 — Conservación de volumen con eventos

Integrando la EDO entre $0$ y $T$:

$$A\,[h(T) - h(0)] = \int_0^T \big(Q_{in} - Q_{out}\big)\,dt \;-\; \int_0^T D(t)\,dt$$

- $\int D\,dt$ se calcula **exacto** a partir de la lista de eventos:
  $\sum_i q_i \cdot (\text{duración del evento } i \text{ dentro de } [0,T])$.
- $\int (Q_{in}-Q_{out})\,dt$ es continua y se integra con la regla del
  trapecio sobre la trayectoria simulada ($\Delta = 0.01$ s).

Con semilla 42, $T = 300$ s y 19 eventos: ambos lados valen 1.519770 m³
(diferencia $10^{-9}$ m³). Se comprueba que **no se crea ni se pierde agua**,
también en presencia de los eventos discretos.

## 7. Prueba 8 — Tratamiento correcto de los eventos discretos

$D(t)$ salta cuando un consumidor abre o cierra. Un integrador de orden alto
solo mantiene su precisión si **no cruza** una discontinuidad dentro de un paso.
`simulation.integrate_interval` parte cada intervalo en los instantes de
inicio/fin de los eventos (`events.breakpoints`) y en cada tramo usa $D$
constante.

Comparación contra una referencia con $\Delta t = 0.001$ s (120 s, semilla 42):

| Δt (s) | Método anterior (sin partir) | Método actual (por tramos) |
|---:|---:|---:|
| 0.100 | 1.95e-05 m | 7.4e-10 m |
| 0.050 | 3.72e-05 m | 2.1e-10 m |
| 0.025 | 7.52e-05 m | 5.4e-11 m |

El método anterior **no convergía** al reducir el paso; el actual sí. (No llega
exactamente a orden 4 porque la saturación de la bomba introduce un "codo" en
$Q_{in}(h)$, pero el error es despreciable.)

## 8. Prueba 9 — Reproducibilidad

Dos corridas con la misma semilla deben producir trayectorias idénticas bit a
bit: máximo $|\Delta h| = 0$. Cada número aleatorio se genera con un
`random.Random` sembrado por (semilla, índice del evento), así que no depende
del orden de ejecución ni del tiempo real. La prueba corre con los eventos en
modo Automático desde $t = 0$.

## 9. Pruebas 10 y 11 — Propiedades estadísticas de los eventos

**Media entre llegadas.** $X \sim \text{Exp}(m)$ con $m = 12$ s, acotado a 1 s.
Por la falta de memoria de la exponencial:

$$E[\max(1, X)] = 1 + E[(X-1)^+] = 1 + m\,e^{-1/m} = 1 + 12\,e^{-1/12} = 12.0405\ \text{s}$$

Con 40 000 muestras: 12.0464 s (0.05 %).

**Demanda media (Ley de Little).** Tasa de llegada $\lambda = 1/12.0405$
eventos/s; $E[q] = (9+23)/2 = 16$ L/s; $E[d] = (6+15)/2 = 10.5$ s
(independientes):

$$\bar D = \lambda\,E[q]\,E[d] = \frac{16 \cdot 10.5}{12.0405} = 13.95\ \text{L/s}$$

Simulando 200 000 s con semilla 7: 13.81 L/s (1 %, dentro de la variabilidad
muestral). En promedio hay $\lambda E[d] \approx 0.87$ consumidores abiertos.

## 10. Comprobaciones a mano desde la interfaz

Pausar la simulación y tomar una fila de la tabla **Registros de la
simulación**:

1. **Presión:** $P = 9.81\,h$ kPa. Ej.: $h = 3.350$ → $P = 32.86$ kPa.
2. **Salida:** $Q_{out} = 1000\,C\sqrt h$ L/s. Ej.: $18\sqrt{3.35} = 32.9$ L/s.
3. **Entrada AUTO:** $Q_{in} = \min(90, \max(0,\ 36 + 120(h_{ref}-h)))$ L/s.
   Ej.: $h = 3.35$ → $36 + 78 = 114$ → satura en 90 L/s.
4. **Diferencia finita:** con dos filas consecutivas ($\Delta t = 0.5$ s),
   $$A\,\frac{h_{k+1}-h_k}{0.5} \approx Q_{in} - Q_{out} - D \quad (\text{promedio de ambas filas, en m}^3/\text{s})$$
   Ej. primer paso en MANUAL desde 3.35 m: $(0.036 - 0.032945)/3 \cdot 0.5 = 0.000509$ m,
   y la app muestra $h = 3.3505$ m.
5. **Equilibrio:** en AUTO, sin eventos activos, el nivel tiende a 4.000 m
   (o 3.812 m con $C = 0.030$), como dice la nota de estabilidad del panel.
6. **Semilla:** reiniciar dos veces con la misma semilla y repetir lo mismo
   (mismos clics de GED, o activar Automático en el mismo instante, p. ej.
   pausando en $t = 0$) → la tabla de eventos muestra los mismos IDs,
   duraciones y caudales.
7. **Interruptor de eventos:** en Manual, sin pulsar GED, la columna D (L/s)
   permanece en 0.0 y el nivel converge sin oscilar; en Automático aparecen
   eventos `E001, E002, …` con separación media ≈ 12 s.

## 11. Alcance de la verificación

- Se verifica la parte continua (EDO + RK4), la parte discreta (generación de
  eventos) y su acoplamiento (balance de volumen, discontinuidades).
- La precisión numérica ($\sim10^{-10}$ m) es muy superior a la que se muestra
  en pantalla (milímetros), así que el error del integrador no afecta lo
  observado.
- No se valida contra datos reales de un acueducto (ver
  [CONTEXTO.md §7](CONTEXTO.md#7-limitaciones-del-modelo)).
