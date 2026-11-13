#ifdef PUI_DRV_SPI

#include "pui_lvgl.h"
#include <lvgl.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>

/* GPIO via /sys/class/gpio (works without root on most RPi setups). */
static int gpio_export(int pin)
{
    char buf[64];
    int fd = open("/sys/class/gpio/export", O_WRONLY);
    if (fd < 0) return -1;
    int n = snprintf(buf, sizeof(buf), "%d", pin);
    write(fd, buf, n);
    close(fd);
    /* Set direction to output. */
    snprintf(buf, sizeof(buf), "/sys/class/gpio/gpio%d/direction", pin);
    fd = open(buf, O_WRONLY);
    if (fd < 0) return -1;
    write(fd, "out", 3);
    close(fd);
    return 0;
}

static void gpio_set(int pin, int value)
{
    char buf[64];
    snprintf(buf, sizeof(buf), "/sys/class/gpio/gpio%d/value", pin);
    int fd = open(buf, O_WRONLY);
    if (fd < 0) return;
    write(fd, value ? "1" : "0", 1);
    close(fd);
}

/* ---- SPI state ---- */

static int s_spi_fd = -1;
static int s_dc_pin = -1;
static int s_rst_pin = -1;
static int s_bl_pin = -1;
static uint8_t *s_fb = NULL;
static lv_display_t *s_disp = NULL;

static void spi_send(const uint8_t *data, size_t len, int is_data)
{
    gpio_set(s_dc_pin, is_data);
    struct spi_ioc_transfer tr = {
        .tx_buf = (unsigned long)data,
        .len = len,
        .speed_hz = 24000000,
    };
    ioctl(s_spi_fd, SPI_IOC_MESSAGE(1), &tr);
}

static void spi_cmd(uint8_t cmd)  { spi_send(&cmd, 1, 0); }
static void spi_data(const uint8_t *d, size_t n) { spi_send(d, n, 1); }

/* ---- ILI9341 init ---- */

static void ili9341_init(int w, int h)
{
    spi_cmd(0x01); usleep(150000); /* SW reset */
    spi_cmd(0x11); usleep(500000); /* Sleep out */
    spi_cmd(0x3A); { uint8_t d = 0x55; spi_data(&d, 1); } /* 16-bit color */
    spi_cmd(0x36); { uint8_t d = 0x48; spi_data(&d, 1); } /* Memory access */
    spi_cmd(0x29); usleep(100000); /* Display on */
}

/* ---- ST7789 init ---- */

static void st7789_init(int w, int h)
{
    spi_cmd(0x01); usleep(150000);
    spi_cmd(0x11); usleep(500000);
    spi_cmd(0x3A); { uint8_t d = 0x55; spi_data(&d, 1); }
    spi_cmd(0x36); { uint8_t d = 0x00; spi_data(&d, 1); }
    spi_cmd(0x21); /* Inversion on (typical for ST7789) */
    spi_cmd(0x29); usleep(100000);
}

/* ---- LVGL flush callback ---- */

static void flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map)
{
    int x1 = area->x1, y1 = area->y1, x2 = area->x2, y2 = area->y2;

    /* Column address set */
    spi_cmd(0x2A);
    uint8_t ca[] = { x1 >> 8, x1 & 0xFF, x2 >> 8, x2 & 0xFF };
    spi_data(ca, 4);

    /* Row address set */
    spi_cmd(0x2B);
    uint8_t ra[] = { y1 >> 8, y1 & 0xFF, y2 >> 8, y2 & 0xFF };
    spi_data(ra, 4);

    /* Memory write */
    spi_cmd(0x2C);
    size_t len = (x2 - x1 + 1) * (y2 - y1 + 1) * 2; /* RGB565 */
    spi_data(px_map, len);

    lv_display_flush_ready(disp);
}

/* ---- Tick callback ---- */

#include <time.h>

static uint32_t tick_get(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

/* ---- Public API ---- */

lv_display_t *pui_drv_spi_init(const pui_display_config_t *cfg)
{
    char path[64];
    snprintf(path, sizeof(path), "/dev/spidev%d.%d", cfg->spi_bus, cfg->spi_device);
    s_spi_fd = open(path, O_RDWR);
    if (s_spi_fd < 0) {
        fprintf(stderr, "pui_lvgl: cannot open %s\n", path);
        return NULL;
    }

    uint8_t mode = SPI_MODE_0;
    uint32_t speed = cfg->baudrate;
    ioctl(s_spi_fd, SPI_IOC_WR_MODE, &mode);
    ioctl(s_spi_fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed);

    s_dc_pin = cfg->dc;
    s_rst_pin = cfg->reset;
    s_bl_pin = cfg->backlight;

    if (s_dc_pin >= 0) gpio_export(s_dc_pin);
    if (s_rst_pin >= 0) {
        gpio_export(s_rst_pin);
        gpio_set(s_rst_pin, 0); usleep(100000);
        gpio_set(s_rst_pin, 1); usleep(100000);
    }
    if (s_bl_pin >= 0) {
        gpio_export(s_bl_pin);
        gpio_set(s_bl_pin, 1);
    }

    if (strcmp(cfg->driver, "ili9341") == 0)
        ili9341_init(cfg->width, cfg->height);
    else
        st7789_init(cfg->width, cfg->height);

    lv_tick_set_cb(tick_get);

    int w = cfg->width, h = cfg->height;
    if (cfg->rotation == 90 || cfg->rotation == 270) { int t = w; w = h; h = t; }

    s_disp = lv_display_create(w, h);
    size_t buf_size = w * h / 10 * 2; /* ~10% of screen, RGB565 */
    s_fb = (uint8_t *)malloc(buf_size);
    lv_display_set_buffers(s_disp, s_fb, NULL, buf_size, LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(s_disp, flush_cb);
    lv_display_set_color_format(s_disp, LV_COLOR_FORMAT_RGB565);

    return s_disp;
}

void pui_drv_spi_deinit(void)
{
    if (s_bl_pin >= 0) gpio_set(s_bl_pin, 0);
    if (s_spi_fd >= 0) { close(s_spi_fd); s_spi_fd = -1; }
    free(s_fb); s_fb = NULL;
    s_disp = NULL;
}

#endif /* PUI_DRV_SPI */
