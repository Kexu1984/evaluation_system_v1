#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include "interface_layer.h"
#include "device_driver.h"
#include "logging.h"

/* Test cases */
static int test_driver_initialization(void) {
    LOG_INFO("=== Test: Driver Initialization ===");

    if (device_init() != DRIVER_OK) {
        LOG_ERROR("Device initialization failed");
        return -1;
    }

    LOG_INFO("PASS: Device initialized successfully");
    return 0;
}

static int test_device_operations(void) {
    LOG_INFO("=== Test: Device Operations ===");

    /* Enable device */
    if (device_enable() != DRIVER_OK) {
        LOG_ERROR("Device enable failed");
        return -1;
    }

    /* Write data */
    uint32_t test_data = 0x12345678;
    if (device_write_data(test_data) != DRIVER_OK) {
        LOG_ERROR("Device write failed");
        return -1;
    }

    /* Read data */
    uint32_t read_data = 0;
    if (device_read_data(&read_data) != DRIVER_OK) {
        LOG_ERROR("Device read failed");
        return -1;
    }

    LOG_INFO("Written: 0x%x, Read: 0x%x", test_data, read_data);

    /* Get status */
    uint32_t status = device_get_status();
    LOG_INFO("Device status: 0x%x", status);

    LOG_INFO("PASS: Device operations completed");
    return 0;
}

static int test_register_access(void) {
    LOG_INFO("=== Test: Direct Register Access ===");

    /* Test direct register access through interface layer */
    uint32_t value = read_register(DEVICE_BASE_ADDR, 4);
    LOG_INFO("Read register value: 0x%x", value);

    if (write_register(DEVICE_BASE_ADDR, 0xAABBCCDD, 4) == 0) {
        LOG_INFO("PASS: Register write successful");
    } else {
        LOG_ERROR("Register write failed");
        return -1;
    }

    return 0;
}

static int run_all_tests(void) {
    LOG_INFO("Starting NewICD3 Interface Layer Tests...");

    int failures = 0;

    if (test_driver_initialization() != 0) failures++;
    if (test_device_operations() != 0) failures++;
    if (test_register_access() != 0) failures++;

    LOG_INFO("=== Test Summary ===");
    if (failures == 0) {
        LOG_INFO("All tests PASSED");
        return 0;
    } else {
        LOG_ERROR("%d test(s) FAILED", failures);
        return -1;
    }
}

/*============================================================================
 *   DMA Memory-to-Memory Transfer Example
 *   This example demonstrates a simple DMA memory-to-memory transfer using
 *============================================================================*/
#define REG_READ(addr)           read_register((addr), 4)
#define REG_WRITE(addr, value)   write_register((addr), (value), 4)

// Register offsets
#define CTRL_REG 0x00
#define STATUS_REG  0x04
#define IRQ_STATUS_REG  0x08
#define IRQ_ENABLE_REG  0x0C

// Channel registers (per channel, starting at 0x10)
#define CHANNEL_BASE  0x10
#define CHANNEL_SIZE  0x20
#define CH_CTRL_OFFSET  0x00
#define CH_SRC_ADDR_OFFSET 0x04
#define CH_DST_ADDR_OFFSET  0x08
#define CH_SIZE_OFFSET  0x0C
#define CH_STATUS_OFFSET  0x10

void dump_memory(const char *str, uint8_t *point, int len) {
    //uint32_t *newp = (uint32_t *)point;
    printf("%s\n", str);
    for (size_t i = 0; i < len; i++) {
        /* code */
        printf("%02x ", point[i]);
    }
    printf("\n");
}

static void dma_mem2mem_transfer(uint32_t *src, uint32_t *dst, size_t size, bool is_irq) {
    uint32_t *dma_base = (uint32_t *)(0x40000000); // Example DMA base address
    REG_WRITE((uint32_t)dma_base + CTRL_REG, 0x01); // Enable DMA c

    // Configure channel 0
    uint32_t *ch_base = (uint32_t *)(0x40000010);
    REG_WRITE((uint32_t)ch_base + CH_SRC_ADDR_OFFSET, (uint32_t)src);
    REG_WRITE((uint32_t)ch_base + CH_DST_ADDR_OFFSET, (uint32_t)dst);
    REG_WRITE((uint32_t)ch_base + CH_SIZE_OFFSET, size);

    if (is_irq) {
        // Enable IRQ for this channel
        REG_WRITE((uint32_t)dma_base + IRQ_ENABLE_REG, 0x100);
    }

    // Start transfer (enable + start + mem2mem mode)
    uint32_t ctrl_value = 0x1 | 0x2 | (0 << 4);  // enable | start | mem2mem
    REG_WRITE((uint32_t)ch_base + CH_CTRL_OFFSET, ctrl_value);
}

static void dma_mem2peri_transfer(uint32_t *src, uint32_t *dst, size_t size, bool is_irq) {
    uint32_t *dma_base = (uint32_t *)(0x40000000); // Example DMA base address
    REG_WRITE((uint32_t)dma_base + CTRL_REG, 0x01); // Enable DMA c

    // Configure channel 0
    uint32_t *ch_base = (uint32_t *)(0x40000010);
    REG_WRITE((uint32_t)ch_base + CH_SRC_ADDR_OFFSET, (uint32_t)src);
    REG_WRITE((uint32_t)ch_base + CH_DST_ADDR_OFFSET, (uint32_t)dst);
    REG_WRITE((uint32_t)ch_base + CH_SIZE_OFFSET, size);

    if (is_irq) {
        // Enable IRQ for this channel
        REG_WRITE((uint32_t)dma_base + IRQ_ENABLE_REG, 0x100);
    }

    // Start transfer (enable + start + mem2peri mode)
    uint32_t ctrl_value = 0x1 | 0x2 | (0x1 << 4) | 0x200;  // enable | start | mem2peri | dst_fixed
    REG_WRITE((uint32_t)ch_base + CH_CTRL_OFFSET, ctrl_value);
}

static void dma_interrupt_callback(uint32_t device_id, uint32_t interrupt_id) {
    uint32_t *src = (uint32_t *)0x20000000; // Source address
    uint32_t *dst = (uint32_t *)0x20001000; // Destination address

    LOG_INFO("DMA %d interrupt received: ID=%d", device_id, interrupt_id);
    dump_memory("Irq Destination Memory", (uint8_t *)0x20001000, 16);

    REG_WRITE((uint32_t)0x40000000 + IRQ_ENABLE_REG, 0);
    // Verify transfer
    for (size_t i = 0; i < 16 / sizeof(uint32_t); i++) {
        if (dst[i] != src[i]) {
            LOG_ERROR("DMA transfer failed at index %zu: expected 0x%x, got 0x%x",
                      i, src[i], dst[i]);
            return ;
        }
    }
    LOG_INFO("DMA transfer OK\n");
}

int test_dma_mem2mem(uint32_t *src, uint32_t *dst, size_t size, bool is_irq) {
    LOG_DEBUG("Source before DMA:");
    dump_memory("Source Memory", (uint8_t *)src, size);

    // Perform DMA transfer
    dma_mem2mem_transfer(src, dst, size, is_irq);

    if (is_irq) {
        /* Register interrupt handler */
        LOG_INFO("register interrupt handler handler=%p\n", dma_interrupt_callback);
        if (register_interrupt_handler(8, dma_interrupt_callback) != 0) {
            LOG_ERROR("Failed to register interrupt handler");
            return DRIVER_ERROR;
        }
        sleep(5); // Wait for interrupt to be processed
    } else {
        LOG_DEBUG("Destination after DMA:");
        dump_memory("Destination Memory", (uint8_t *)dst, size);
        // Verify transfer
        for (size_t i = 0; i < size / sizeof(uint32_t); i++) {
            if (dst[i] != src[i]) {
                LOG_ERROR("DMA transfer failed at index %zu: expected 0x%x, got 0x%x",
                        i, src[i], dst[i]);
                return 1;
            }
        }
    }

    return 0;
}

int test_dma_mem2peri(uint8_t *src, uint32_t *dst, size_t size, bool is_irq) {
    // Perform DMA transfer
    dma_mem2peri_transfer(src, dst, size, is_irq);

    if (is_irq) {
        /* Register interrupt handler */
        LOG_INFO("register interrupt handler handler=%p\n", dma_interrupt_callback);
        if (register_interrupt_handler(8, dma_interrupt_callback) != 0) {
            LOG_ERROR("Failed to register interrupt handler");
            return DRIVER_ERROR;
        }
        sleep(5); // Wait for interrupt to be processed
    } else {
        /* Polling dma status if done */
        uint32_t ch_status = REG_READ((uint32_t)0x40000010 + CH_STATUS_OFFSET);
        while (!(ch_status & 0x4)) {
            sleep(1);
            ch_status = REG_READ((uint32_t)0x40000010 + CH_STATUS_OFFSET);
        }
    }
    LOG_DEBUG("DMA transfer finished");

    return 0;
}

int main(int argc __attribute__((unused)), char *argv[] __attribute__((unused))) {
    uint8_t *src;
    uint32_t *dst;
    uint32_t *crc_res;
    size_t size;
    int result;

    LOG_INFO("NewICD3 Universal IC Simulator");
    LOG_INFO("==============================");

    /* Initialize interface layer */
    if (interface_layer_init() != 0) {
        LOG_ERROR("Failed to initialize interface layer");
        return EXIT_FAILURE;
    }

    /* Register device with interface layer */
    if (register_device(1, 0x20000000, 0x10000) != 0) {
        printf("Failed to register device\n");
        return DRIVER_ERROR;
    }
    if (register_device(1, 0x40000000, 0x10000) != 0) {
        printf("Failed to register device\n");
        return DRIVER_ERROR;
    }

    size = 16;
    src = (uint8_t *)0x20000000; // Source address
    dst = (uint32_t *)0x20001000; // Destination address
    for (size_t i = 0; i < size / sizeof(uint32_t); i++) {
        dst[i] = 0; // Fill with test data
    }
    for (size_t i = 0; i < size; i++) {
        src[i] = i + 1; // Fill with test data
    }
    result = test_dma_mem2mem(src, dst, size, false);
    if (result != 0) {
        LOG_ERROR("DMA memory-to-memory without irq test failed");
        return EXIT_FAILURE;
    }

    for (size_t i = 0; i < size / sizeof(uint32_t); i++) {
        dst[i] = 0; // Fill with test data
    }
    for (size_t i = 0; i < size; i++) {
        src[i] = i + 1; // Fill with test data
    }
    result = test_dma_mem2mem(src, dst, size, true);
    if (result != 0) {
        LOG_ERROR("DMA memory-to-memory with irq test failed");
        return EXIT_FAILURE;
    }

    src = (uint8_t *)0x20000000; // Source address
    dst = (uint32_t *)0x40001008; // Destination address: CRC data register
    size = 5; // Size in bytes

    // Initialize source memory
    *src = 'H';
    *(src + 1) = 'e';
    *(src + 2) = 'l';
    *(src + 3) = 'l';
    *(src + 4) = 'o';
    *(src + 5) = 0;
    *(src + 6) = 0;
    *(src + 7) = 0;
    // config crc device
    REG_WRITE(0x40001000, 0); // crc16 mode
    REG_WRITE(0x40001004, 0xFFFF); // reset initial value

    result = test_dma_mem2peri(src, dst, 4, false);
    if (result != 0) {
        LOG_ERROR("DMA memory-to-memory with irq test failed");
        return EXIT_FAILURE;
    }
    // crc read result
    printf("CRC16 result-CCITT: 0x%08x\n", REG_READ(0x40001004));

    REG_WRITE(0x40001000, 1); // crc32 mode
    REG_WRITE(0x40001004, 0xFFFFFFFF); // reset initial value
    result = test_dma_mem2peri(src, dst, 4, false);
    if (result != 0) {
        LOG_ERROR("DMA memory-to-memory with irq test failed");
        return EXIT_FAILURE;
    }
    // crc read result
    printf("CRC32 result-CCITT: 0x%08x\n", REG_READ(0x40001004));

    /* Cleanup */
    //device_deinit();
    interface_layer_deinit();

    LOG_INFO("System shutdown complete.");

    return (result == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}