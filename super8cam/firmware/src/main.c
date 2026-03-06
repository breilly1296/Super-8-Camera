/**
 * main.c — Super 8 Camera firmware entry point.
 *
 * Initializes all peripherals (GPIO, ADC, timers, PWM, interrupts),
 * runs state_machine_update() in a 1 ms superloop, and outputs UART
 * debug telemetry at 115200 baud every 500 ms.
 *
 * Target: STM32L031K6 (HSI16, bare-register CMSIS)
 */

#include "stm32l0xx.h"
#include "config.h"
#include "pinmap.h"
#include "motor_control.h"
#include "metering.h"
#include "encoder.h"
#include "state_machine.h"

volatile uint32_t g_tick_ms = 0;

void SysTick_Handler(void) { g_tick_ms++; }

/* ---- Clock init: HSI16, no PLL ---- */
static void clock_init(void)
{
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY));
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_HSI;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_HSI);
}

/* ---- UART2 on PA2 (TX) for debug output ---- */
static void uart_init(void)
{
    RCC->IOPENR  |= RCC_IOPENR_GPIOAEN;
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN;

    /* PA2: AF4 = USART2_TX */
    GPIOA->MODER  = (GPIOA->MODER  & ~(3U << (2 * 2))) | (2U << (2 * 2));
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFU << (2 * 4))) | (4U << (2 * 4));

    USART2->BRR = SYS_CLOCK_HZ / UART_BAUD;
    USART2->CR1 = USART_CR1_TE | USART_CR1_UE;
}

static void uart_putc(char c)
{
    while (!(USART2->ISR & USART_ISR_TXE));
    USART2->TDR = (uint8_t)c;
}

static void uart_puts(const char *s)
{
    while (*s) uart_putc(*s++);
}

static void uart_put_int(int32_t val)
{
    char buf[12];
    int i = 0;
    if (val < 0) { uart_putc('-'); val = -val; }
    if (val == 0) { uart_putc('0'); return; }
    while (val > 0) { buf[i++] = '0' + (val % 10); val /= 10; }
    while (i > 0) uart_putc(buf[--i]);
}

static void uart_put_float1(float val)
{
    if (val < 0) { uart_putc('-'); val = -val; }
    int32_t whole = (int32_t)val;
    int32_t frac = (int32_t)((val - (float)whole) * 10.0f);
    uart_put_int(whole);
    uart_putc('.');
    uart_putc('0' + (char)(frac % 10));
}

/* ---- GPIO init for inputs with pull-ups ---- */
static void gpio_init(void)
{
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN;

    /* PB0 trigger: input with pull-up */
    GPIOB->MODER &= ~(3U << (PIN_TRIGGER_PIN * 2));
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3U << (PIN_TRIGGER_PIN * 2)))
                 |  (1U << (PIN_TRIGGER_PIN * 2));

    /* PB1 FPS select: input with pull-up */
    GPIOB->MODER &= ~(3U << (PIN_FPS_SEL_PIN * 2));
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3U << (PIN_FPS_SEL_PIN * 2)))
                 |  (1U << (PIN_FPS_SEL_PIN * 2));

    /* PB3, PB4 DIP switches: input with pull-up */
    GPIOB->MODER &= ~(3U << (PIN_DIP0_PIN * 2));
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3U << (PIN_DIP0_PIN * 2)))
                 |  (1U << (PIN_DIP0_PIN * 2));
    GPIOB->MODER &= ~(3U << (PIN_DIP1_PIN * 2));
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3U << (PIN_DIP1_PIN * 2)))
                 |  (1U << (PIN_DIP1_PIN * 2));

    /* PA11 cartridge detect: input with pull-up */
    GPIOA->MODER &= ~(3U << (PIN_CART_DET_PIN * 2));
    GPIOA->PUPDR = (GPIOA->PUPDR & ~(3U << (PIN_CART_DET_PIN * 2)))
                 |  (1U << (PIN_CART_DET_PIN * 2));
}

/* ---- Debug telemetry over UART every 500 ms ---- */
static void debug_output(void)
{
    static uint32_t next_debug = 0;
    uint32_t now = g_tick_ms;
    if (now < next_debug) return;
    next_debug = now + UART_DEBUG_INTERVAL_MS;

    uart_puts(state_machine_get_state_name());
    uart_puts(" fps=");
    uart_put_float1(motor_get_fps());
    uart_puts(" duty=");
    uart_put_int(motor_get_duty());
    uart_puts(" ev=");
    uart_put_float1(meter_get_ev());
    uart_puts(" f/");
    uart_put_float1(meter_get_fstop());
    uart_puts(" asa=");
    uart_put_int(meter_get_asa());
    uart_puts(" bat=");
    uart_put_int(meter_get_battery_mv());
    uart_puts("mV frm=");
    uart_put_int((int32_t)state_machine_get_frame_count());
    uart_puts("\r\n");
}

int main(void)
{
    clock_init();

    /* SysTick: 1 ms interrupt */
    SysTick->LOAD = SYSTICK_RELOAD;
    SysTick->VAL  = 0;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk
                  | SysTick_CTRL_TICKINT_Msk
                  | SysTick_CTRL_ENABLE_Msk;

    gpio_init();
    uart_init();
    motor_init();   /* also inits encoder and TIM2 PWM */
    meter_init();
    state_machine_init();

    for (;;) {
        state_machine_update();
        debug_output();

        /* Low-power wait for next SysTick if idle */
        if (state_machine_get_state() == APP_IDLE) {
            __WFI();
        }
    }
}

void HardFault_Handler(void)
{
    TIM2->CCR1 = 0;
    PIN_MOTOR_EN_PORT->BSRR = (1U << (PIN_MOTOR_EN_PIN + 16));
    for (;;) __WFI();
}
