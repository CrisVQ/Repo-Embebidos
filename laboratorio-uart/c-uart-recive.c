#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include "inc/hw_memmap.h"
#include "driverlib/debug.h"
#include "driverlib/gpio.h"
#include "driverlib/sysctl.h"
#include "driverlib/pin_map.h"
#include "driverlib/uart.h"
#include "utils/uartstdio.c"

// Prototipos de funciones
void ConfigurarSistema(void);
void ConfigurarUART(void);
void ConfigurarGPIO(void);

int main(void)
{
    //char msg[] = "Hello from Tiva C\n";
    char receivedChar;

    // Configuraciones iniciales del sistema
    ConfigurarSistema();
    ConfigurarGPIO();
    ConfigurarUART();

    // Bucle principal
    while(1)
    {
        // Enviar mensaje por UART
        //UARTprintf(msg);

        // Espera de 1 segundo
        //SysCtlDelay(120000000 / 3); // Aproximadamente 1 segundo de retraso


        // Espera a que haya un carácter disponible en UART
        if(UARTCharsAvail(UART0_BASE))
        {
            receivedChar = UARTCharGet(UART0_BASE);  // Lee el carácter recibido

            // Enciende el LED si recibe el carácter 'A'
            if(receivedChar == 'A')
            {
                UARTprintf("Recibido en Tiva: %c, LED Encendido\n", receivedChar);
                GPIOPinWrite(GPIO_PORTN_BASE, GPIO_PIN_0, GPIO_PIN_0);  // Enciende el LED
            }
            // Apaga el LED si recibe el carácter 'B'
            else if(receivedChar == 'B')
            {
                UARTprintf("Recibido en Tiva: %c, LED Apagado\n", receivedChar);
                GPIOPinWrite(GPIO_PORTN_BASE, GPIO_PIN_0, 0);  // Apaga el LED
            }
        }
    }
}

// Función para configurar el reloj del sistema
void ConfigurarSistema(void)
{
    SysCtlClockFreqSet((SYSCTL_XTAL_25MHZ | SYSCTL_OSC_MAIN | SYSCTL_USE_PLL | SYSCTL_CFG_VCO_480), 120000000);
}

// Función para configurar los periféricos UART
void ConfigurarUART(void)
{
    SysCtlPeripheralEnable(SYSCTL_PERIPH_UART0);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOA);

    // Configurar los pines para UART0
    GPIOPinConfigure(GPIO_PA0_U0RX);
    GPIOPinConfigure(GPIO_PA1_U0TX);
    GPIOPinTypeUART(GPIO_PORTA_BASE, GPIO_PIN_0 | GPIO_PIN_1);

    // Configurar UART0 con baudrate de 9600
    UARTStdioConfig(0, 9600, 120000000);
}

// Función para configurar los pines GPIO
void ConfigurarGPIO(void)
{
    // Habilitar el puerto para el LED (PN0) y el botón (PJ0)
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPION);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOJ);

    // Configurar PN0 como salida
    GPIOPinTypeGPIOOutput(GPIO_PORTN_BASE, GPIO_PIN_0);

    // Configurar PJ0 como entrada con resistencia pull-up
    GPIOPinTypeGPIOInput(GPIO_PORTJ_BASE, GPIO_PIN_0);
    GPIOPadConfigSet(GPIO_PORTJ_BASE, GPIO_PIN_0, GPIO_STRENGTH_2MA, GPIO_PIN_TYPE_STD_WPU);
}
