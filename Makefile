# =========================================================================
# Makefile — Super 8 Camera Firmware (STM32L0xx, ARM GCC)
# =========================================================================
#
# Usage:
#   make              Build firmware ELF + BIN + HEX
#   make flash        Flash via ST-Link (OpenOCD)
#   make clean        Remove build artifacts
#   make size         Show code/data size breakdown
#
# Prerequisites:
#   - arm-none-eabi-gcc toolchain
#   - STM32L0xx CMSIS headers (set CMSIS_DIR below)
#   - OpenOCD (optional, for flashing)
# =========================================================================

# ---- Project -----------------------------------------------------------
TARGET   = super8_camera
BUILD    = build

# ---- Sources -----------------------------------------------------------
C_SRCS   = main.c motor_control.c metering.c
# Add your startup file (ASM) here — e.g. from STM32CubeL0:
ASM_SRCS = startup_stm32l031xx.s

# ---- Toolchain ---------------------------------------------------------
PREFIX   = arm-none-eabi-
CC       = $(PREFIX)gcc
AS       = $(PREFIX)gcc
LD       = $(PREFIX)gcc
OBJCOPY  = $(PREFIX)objcopy
SIZE     = $(PREFIX)size

# ---- MCU flags ---------------------------------------------------------
CPU      = -mcpu=cortex-m0plus
FPU      =
FLOAT    = -mfloat-abi=soft
MCU      = $(CPU) -mthumb $(FPU) $(FLOAT)

# ---- CMSIS / HAL paths ------------------------------------------------
# Point these at your local STM32CubeL0 installation or CMSIS pack.
# Only CMSIS device headers are needed (no HAL).
CMSIS_DIR     ?= ../STM32CubeL0/Drivers/CMSIS
CMSIS_DEV_DIR ?= $(CMSIS_DIR)/Device/ST/STM32L0xx
CMSIS_INC      = $(CMSIS_DIR)/Include
DEVICE_INC     = $(CMSIS_DEV_DIR)/Include

# ---- Linker script -----------------------------------------------------
# Use the appropriate LD script for your exact chip.
# STM32L031K6: 32 KB Flash, 8 KB RAM
LDSCRIPT ?= STM32L031K6Tx_FLASH.ld

# ---- Compiler flags ----------------------------------------------------
CFLAGS   = $(MCU)
CFLAGS  += -std=c11 -Wall -Wextra -Wpedantic -Wshadow
CFLAGS  += -ffunction-sections -fdata-sections
CFLAGS  += -Os -g3
CFLAGS  += -DSTM32L031xx
CFLAGS  += -I. -I$(CMSIS_INC) -I$(DEVICE_INC)

# Math library for log2f / sqrtf / powf in metering.c
LDFLAGS  = $(MCU)
LDFLAGS += -T$(LDSCRIPT)
LDFLAGS += -Wl,--gc-sections
LDFLAGS += -specs=nosys.specs -specs=nano.specs
LDFLAGS += -lm
LDFLAGS += -Wl,-Map=$(BUILD)/$(TARGET).map,--cref

# ---- Assembler flags ---------------------------------------------------
ASFLAGS  = $(MCU) -x assembler-with-cpp

# ---- Object files ------------------------------------------------------
OBJS  = $(addprefix $(BUILD)/, $(C_SRCS:.c=.o))
OBJS += $(addprefix $(BUILD)/, $(ASM_SRCS:.s=.o))

# ---- Build rules -------------------------------------------------------

.PHONY: all clean flash size

all: $(BUILD)/$(TARGET).elf $(BUILD)/$(TARGET).bin $(BUILD)/$(TARGET).hex size

$(BUILD)/%.o: %.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/%.o: %.s | $(BUILD)
	$(AS) $(ASFLAGS) -c $< -o $@

$(BUILD)/$(TARGET).elf: $(OBJS)
	$(LD) $(LDFLAGS) $^ -o $@

$(BUILD)/$(TARGET).bin: $(BUILD)/$(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(BUILD)/$(TARGET).hex: $(BUILD)/$(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

$(BUILD):
	mkdir -p $(BUILD)

size: $(BUILD)/$(TARGET).elf
	$(SIZE) --format=berkeley $<

clean:
	rm -rf $(BUILD)

# ---- Flash via OpenOCD -------------------------------------------------
OPENOCD      ?= openocd
OPENOCD_CFG  ?= board/stm32l0discovery.cfg

flash: $(BUILD)/$(TARGET).bin
	$(OPENOCD) -f $(OPENOCD_CFG) \
	  -c "program $(BUILD)/$(TARGET).bin verify reset exit 0x08000000"

# ---- Optional: PlatformIO alternative ----------------------------------
# If you prefer PlatformIO, use platformio.ini instead of this Makefile.
# See platformio.ini in this directory.
