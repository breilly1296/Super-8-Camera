/**
 * main.c — Super 8 Camera firmware entry point.
 * Initializes all subsystems, runs the state machine superloop.
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

static void clock_init(void)
{
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY));
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_HSI;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_HSI);
}

int main(void)
{
    clock_init();
    SysTick->LOAD = 16000U - 1U;
    SysTick->VAL = 0;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_ENABLE_Msk;

    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN;

    motor_init();
    meter_init();
    state_machine_init();

    for (;;) {
        state_machine_update();
    }
}

void HardFault_Handler(void) { TIM2->CCR1 = 0; for (;;) __WFI(); }
