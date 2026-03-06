/**
 * main.c — Super 8 Camera Firmware Entry Point
 *
 * Responsibilities:
 *   - HSI16 clock configuration (16 MHz)
 *   - SysTick at 1 kHz (1 ms tick)
 *   - GPIO init for main-owned pins (LEDs, EXTI trigger/FPS)
 *   - USART2 debug output at 115200 baud (500 ms interval)
 *   - Subsystem initialization (motor, metering, state machine)
 *   - Superloop: state_machine_update() every tick
 *   - Low-power WFI sleep between ticks
 *
 * Target: STM32L031K6 at 16 MHz HSI.
 *
 * Pin allocation summary (see pinmap.h for complete table):
 *   PA0  TIM2_CH1   motor PWM
 *   PA1              FPS select (EXTI1)
 *   PA2              trigger (EXTI2, active low)
 *   PA3              fault/warning LED
 *   PA4  TIM22_CH1  galvanometer PWM
 *   PA5              green LED
 *   PA6              red LED
 *   PA7  ADC_IN7    photodiode
 *   PA9  USART2_TX  debug UART
 *   PA10 USART2_RX  debug UART
 *   PB0              DIP bit 0 (ASA)
 *   PB1              DIP bit 1 (ASA)
 *   PB2              low-battery LED
 *   PB4  TIM21_CH1  encoder input capture
 *   PB5              cartridge-empty LED
 *
 * Copyright (c) 2026 — released under MIT license.
 */

#include "stm32l0xx.h"
#include "config.h"
#include "pinmap.h"
#include "motor_control.h"
#include "metering.h"
#include "encoder.h"
#include "state_machine.h"
#include <stdint.h>

/* =====================================================================
 * Global millisecond tick — read by all modules via `extern`
 * ===================================================================== */

volatile uint32_t g_tick_ms = 0;

void SysTick_Handler(void)
{
    g_tick_ms++;
}

/* =====================================================================
 * Clock: HSI16 at 16 MHz
 * ===================================================================== */

static void clock_init(void)
{
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) { /* wait */ }

    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_HSI;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_HSI) { /* wait */ }
}

static void systick_init(void)
{
    SysTick->LOAD = SYS_TICK_RELOAD;
    SysTick->VAL  = 0;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk
                  | SysTick_CTRL_TICKINT_Msk
                  | SysTick_CTRL_ENABLE_Msk;
}

/* =====================================================================
 * GPIO init for main.c-owned pins
 *
 * Subsystem GPIOs (motor PWM, encoder, ADC, galvo, exposure LEDs)
 * are initialized by motor_init() and meter_init().
 * ===================================================================== */

static void gpio_init(void)
{
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN;

    /* PA1: FPS select — input with pull-down */
    PIN_FPS_SEL_PORT->MODER &= ~(3U << (PIN_FPS_SEL_PIN * 2));
    PIN_FPS_SEL_PORT->PUPDR =
        (PIN_FPS_SEL_PORT->PUPDR & ~(3U << (PIN_FPS_SEL_PIN * 2)))
        | (2U << (PIN_FPS_SEL_PIN * 2));

    /* PA2: Trigger — input (external pull-up assumed) */
    PIN_TRIGGER_PORT->MODER &= ~(3U << (PIN_TRIGGER_PIN * 2));

    /* PB2: low-battery LED — output push-pull */
    PIN_LED_LOWBAT_PORT->MODER =
        (PIN_LED_LOWBAT_PORT->MODER & ~(3U << (PIN_LED_LOWBAT_PIN * 2)))
        | (1U << (PIN_LED_LOWBAT_PIN * 2));

    /* PB5: cartridge-empty LED — output push-pull */
    PIN_LED_CART_PORT->MODER =
        (PIN_LED_CART_PORT->MODER & ~(3U << (PIN_LED_CART_PIN * 2)))
        | (1U << (PIN_LED_CART_PIN * 2));

    /* Turn LEDs off */
    PIN_LED_LOWBAT_PORT->BSRR = (1U << (PIN_LED_LOWBAT_PIN + 16));
    PIN_LED_CART_PORT->BSRR   = (1U << (PIN_LED_CART_PIN + 16));
}

/* =====================================================================
 * USART2 — Debug output (PA9 TX, PA10 RX, 115200 baud)
 *
 * Non-blocking transmit via polling TXFE flag.
 * ===================================================================== */

static void uart_init(void)
{
    /* Enable clocks */
    RCC->IOPENR  |= RCC_IOPENR_GPIOAEN;
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN;

    /* PA9: USART2_TX — AF4 */
    PIN_UART_TX_PORT->MODER =
        (PIN_UART_TX_PORT->MODER & ~(3U << (PIN_UART_TX_PIN * 2)))
        | (2U << (PIN_UART_TX_PIN * 2));
    PIN_UART_TX_PORT->AFR[1] =
        (PIN_UART_TX_PORT->AFR[1] & ~(0xFU << ((PIN_UART_TX_PIN - 8) * 4)))
        | (PIN_UART_TX_AF << ((PIN_UART_TX_PIN - 8) * 4));

    /* PA10: USART2_RX — AF4 */
    PIN_UART_RX_PORT->MODER =
        (PIN_UART_RX_PORT->MODER & ~(3U << (PIN_UART_RX_PIN * 2)))
        | (2U << (PIN_UART_RX_PIN * 2));
    PIN_UART_RX_PORT->AFR[1] =
        (PIN_UART_RX_PORT->AFR[1] & ~(0xFU << ((PIN_UART_RX_PIN - 8) * 4)))
        | (PIN_UART_RX_AF << ((PIN_UART_RX_PIN - 8) * 4));

    /* Baud rate: 16 MHz / 115200 ≈ 139 */
    USART2->BRR = SYS_HSI_HZ / UART_BAUDRATE;

    /* Enable TX + USART */
    USART2->CR1 = USART_CR1_TE | USART_CR1_UE;
}

/** Transmit a single character (blocking, but fast at 115200). */
static void uart_putc(char c)
{
    while (!(USART2->ISR & USART_ISR_TXE)) { /* wait */ }
    USART2->TDR = (uint8_t)c;
}

/** Transmit a null-terminated string. */
static void uart_puts(const char *s)
{
    while (*s) {
        if (*s == '\n') uart_putc('\r');
        uart_putc(*s++);
    }
}

/** Transmit an unsigned integer as decimal string. */
static void uart_putu(uint32_t val)
{
    char buf[11];
    int  i = 0;

    if (val == 0) {
        uart_putc('0');
        return;
    }

    while (val > 0) {
        buf[i++] = '0' + (char)(val % 10);
        val /= 10;
    }
    while (i > 0)
        uart_putc(buf[--i]);
}

/** Transmit a float with 1 decimal place. */
static void uart_putf1(float val)
{
    if (val < 0.0f) {
        uart_putc('-');
        val = -val;
    }
    uint32_t integer = (uint32_t)val;
    uint32_t frac    = (uint32_t)((val - (float)integer) * 10.0f + 0.5f);
    if (frac >= 10) { integer++; frac = 0; }
    uart_putu(integer);
    uart_putc('.');
    uart_putc('0' + (char)frac);
}

/* =====================================================================
 * Debug telemetry — printed every UART_DEBUG_INTERVAL_MS
 *
 * Format (one line, tab-separated):
 *   STATE  FPS_TARGET  FPS_ACTUAL  DUTY  EV  f/STOP  ASA  VBAT  FRAMES
 * ===================================================================== */

static uint32_t last_debug_ms = 0;

static void debug_print(void)
{
    uint32_t now = g_tick_ms;
    if ((now - last_debug_ms) < UART_DEBUG_INTERVAL_MS)
        return;
    last_debug_ms = now;

    uart_puts(state_machine_state_name());
    uart_putc('\t');

    uart_putu(motor_read_target_fps());
    uart_putc('\t');

    uart_putf1(motor_get_fps());
    uart_putc('\t');

    uart_putu(motor_get_duty());
    uart_putc('\t');

    uart_putf1(meter_get_ev());
    uart_putc('\t');

    uart_puts("f/");
    uart_putf1(meter_get_fstop());
    uart_putc('\t');

    uart_putu(meter_get_asa());
    uart_putc('\t');

    uart_putu(state_machine_get_vbat_mv());
    uart_puts("mV\t");

    uart_putu(state_machine_get_frame_count());
    uart_puts("\n");
}

/* =====================================================================
 * Fault handlers
 * ===================================================================== */

void HardFault_Handler(void)
{
    /* Kill motor, light fault LED, halt */
    TIM2->CCR1 = 0;
    PIN_LED_WARN_PORT->BSRR = (1U << PIN_LED_WARN_PIN);
    for (;;) { __WFI(); }
}

void NMI_Handler(void)    { for (;;) { __WFI(); } }
void SVC_Handler(void)    { for (;;) { __WFI(); } }
void PendSV_Handler(void) { for (;;) { __WFI(); } }

/* =====================================================================
 * Entry point
 * ===================================================================== */

int main(void)
{
    /* ---- Clock & tick ---- */
    clock_init();
    systick_init();

    /* ---- GPIO (main-owned pins) ---- */
    gpio_init();

    /* ---- Debug UART ---- */
    uart_init();
    uart_puts("\n[super8cam] firmware starting\n");

    /* ---- Subsystems ---- */
    motor_init();
    meter_init();
    state_machine_init();

    uart_puts("[super8cam] all systems ready\n");

    /* ---- Superloop ---- */
    for (;;) {
        state_machine_update();
        debug_print();

        /* Low-power sleep until next interrupt (SysTick, TIM21, etc.)
         * Saves ~30% power vs busy-wait on L0 series. */
        __WFI();
    }
}
