# DMA App Note

## 1. 简介

DMA（Direct Memory Access，直接存储器访问）用于在外设与存储器之间、或存储器与存储器之间进行高速数据传输。通过 DMA，数据可以在无 CPU 干预的情况下快速搬移，从而释放 CPU 资源去执行其他任务。

AC7840 系列的 DMA 控制器总共有 16 个通道，每个通道可独立配置，用于管理来自一个或多个外设的存储器访问请求。DMA 内部集成仲裁器，用于处理各个 DMA 请求的优先级。

## 2. 特性

* 16 个可独立配置的通道（请求源）。
* 每个通道支持所有外设请求，也支持软件触发（存储器到存储器传输），配置通过软件完成。
* 通道间优先级可由软件配置（4 级：非常高、高、中、低），当优先级相同则硬件采用轮询（Round Robin）方式。
* 支持独立的源和目的数据传输宽度（字节、半字、字），源/目的地址必须与数据宽度对齐。
* 支持源和目的的循环缓冲管理。
* 每个通道有 3 个事件标志（半传输完成、传输完成、传输错误），通过单一中断请求输出。
* 支持存储器到存储器、外设到存储器、存储器到外设、外设到外设传输。
* 支持访问 SRAM、APB 外设作为源和目的。
* 可编程传输数据量，最大支持 32768。

> FIFO RAM 宽度为 32 位，深度为 128，每个通道占用 8 条数据。FIFO 控制逻辑模块通过读写计数器控制 FIFO 的数据读写。

## 3. DMA 请求映射

举例说明外设通道。

| Slot_Num | Module   | DMA_Request              | Description                                                                          | Instance |
| -------- | -------- | ------------------------ | ------------------------------------------------------------------------------------ | -------- |
| 0        | RESERVED | RESERVED                 |                                                                                      | RESERVED |
| 1        | UART     | Receive DMA Request      | UART RX data register/ FIFO is not empty, which trigger DMA to move data to memory.  | UART0    |
| 2        | UART     | Transmit DMA Request     | UART TX data register/ FIFO is not full, which trigger DMA to move data from memory. | UART0    |
| 3        | UART     | Receive DMA Request      | UART RX data register/ FIFO is not empty, which trigger DMA to move data to memory.  | UART1    |
| 4        | UART     | Transmit DMA Request     | UART TX data register/ FIFO is not full, which trigger DMA to move data from memory. | UART1    |
| 5        | UART     | Receive DMA Request      | UART RX data register/ FIFO is not empty, which trigger DMA to move data to memory.  | UART2    |
| 6        | UART     | Transmit DMA Request     | UART TX data register/ FIFO is not full, which trigger DMA to move data from memory. | UART2    |
| 7        | UART     | Receive DMA Request      | UART RX data register/ FIFO is not empty, which trigger DMA to move data to memory.  | UART3    |
| 8        | UART     | Transmit DMA Request     | UART TX data register/ FIFO is not full, which trigger DMA to move data from memory. | UART3    |
| 9        | UART     | Receive DMA Request      | UART RX data register/ FIFO is not empty, which trigger DMA to move data to memory.  | UART4    |
| 10       | UART     | Transmit DMA Request     | UART TX data register/ FIFO is not full, which trigger DMA to move data from memory. | UART4    |
| 11       | UART     | Receive DMA Request      | UART RX data register/ FIFO is not empty, which trigger DMA to move data to memory.  | UART5    |
| 12       | UART     | Transmit DMA Request     | UART TX data register/ FIFO is not full, which trigger DMA to move data from memory. | UART5    |
| 13       | EIO      | EIO Shifter0 DMA Request | Shifter Status flag is set.                                                          | EIO      |
| 14       | EIO      | EIO Shifter1 DMA Request | Shifter Status flag is set.                                                          | EIO      |
| 15       | EIO      | EIO Shifter2 DMA Request | Shifter Status flag is set.                                                          | EIO      |
| 16       | EIO      | EIO Shifter3 DMA Request | Shifter Status flag is set.                                                          | EIO      |

> 表格中描述了每个 Slot 对应的模块、DMA 请求类型及触发条件，例如 UART RX FIFO 非空触发接收 DMA 请求、PWM 通道数据到达预设传输数量触发请求等。

## 4. 仲裁器（Arbiter）

仲裁器根据通道优先级处理请求并启动访问序列。

优先级分两级管理：

* **软件优先级** ：通过 `CHANNELx_CONFIG` 寄存器配置，分为：
* 非常高（Very High）
* 高（High）
* 中（Medium）
* 低（Low）
* **硬件优先级（同一通道内部）** ：

1. 非常高：外设 → 通道内部 RAM
2. 高：通道内部 RAM → 外设
3. 中：SRAM → 通道内部 RAM
4. 低：通道内部 RAM → SRAM

同一通道中，响应外设请求的优先级高于其他请求，且读操作优先于写操作。

## 5. 配置指南

除 `CHANNELx_CHAN_ENABLE` 寄存器外，其他寄存器应在使能前配置完成。参数在 `CHAN_ENABLE` 上升沿生效，当其为高时，不应修改配置参数。

## 6. 复位机制

* **温复位（Warm Reset）** ：当前传输完成后复位，不会造成总线挂起。
* **硬复位（Hard Reset）** ：立即复位，可能导致总线协议中断，引起系统挂起。

全局温复位/硬复位可通过全局控制寄存器设置，硬件会在复位动作完成后自动清零相应位。

## 7. 暂停与恢复

1. 启动 DMA（配置参数后 `CHAN_ENABLE=1`）。
2. 暂停 DMA（`STOP=1`）。
3. 恢复 DMA（`STOP=0`）。
4. 等待 DMA 完成（`CHAN_ENABLE` 自动清零并产生中断）。

暂停不会立即生效，DMA 会等待当前事务完成。

## 8. 循环模式（Circular Mode）

循环模式可用于连续数据流（如 ADC 扫描）。在配置时使能 `CHAN_CIRCULAR` 位，DMA 会自动重新加载传输数量并持续响应请求。

注意：

* DMA 主机不会读/写 `MEM_END_ADDR`，而是 `MEM_END_ADDR - 0x4`。
* 源地址和目的地址均支持循环模式。

## 9. 各外设的 DMA 使用说明

* **GPIO** ：类似 UART，准备好数据后发送请求，DMA 响应搬移。
* **PWM** ：当预设传输数量到达时，DMA 发送 EOT-1 信号到 PWM 引擎，由 PWM 决定是否 ACK/NACK。
* **I2C** ：到达预设数量时，DMA 向 I2C 引擎发送 EOT-1 信号，由 I2C 决定 ACK/NACK。

## 10. 源/目的数据宽度独立传输

DMA 支持源和目的端不同的数据宽度（8、16、32 位）。文档中举例说明了各种宽度组合下数据的读取与写入顺序。

## 11. 地址偏移

源地址（SOFFSET）和目的地址（DOFFSET）支持偏移，偏移值会在每次读写完成后加到当前地址，形成下一地址。

## 12. 状态标志与中断

* **状态标志** ：包括完成、半完成、源/目的总线错误、地址错误、偏移错误、长度错误等，需写 0 清除。
* **中断标志** ：支持半完成、完成、错误中断，每个 DMA 通道有独立的 IRQ Handler。

## 13. 传输模式

* **存储器到存储器（Mem2Mem）** ：需将 `REQ_ID` 设为 Always Enabled，忽略方向位。
* **存储器与外设间传输** ：需正确设置传输方向，DMA 才能响应外设请求。
