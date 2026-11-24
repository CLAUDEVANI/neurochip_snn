`default_nettype none
`timescale 1ns / 1ps

module tt_um_neurochip_snn (
    input  wire [7:0] ui_in,    // Entradas dedicadas
    output wire [7:0] uo_out,   // Saídas dedicadas
    input  wire [7:0] uio_in,   // IOs bidirecionais (entrada)
    output wire [7:0] uio_out,  // IOs bidirecionais (saída)
    output wire [7:0] uio_oe,   // Habilitação de saída dos IOs (1=saída, 0=entrada)
    input  wire       ena,      // Habilita o projeto quando selecionado no chip
    input  wire       clk,      // Clock do sistema
    input  wire       rst_n     // Reset ativo em nível baixo
);

    wire       aer_out_valid;
    wire [1:0] aer_out_addr;

    // Mapeamento dos pinos do Tiny Tapeout:
    // ui_in[0] = en (enable do núcleo)
    // ui_in[1] = aer_in_valid
    // ui_in[2] = aer_in_addr
    aer_top u_core (
        .clk(clk),
        .rst_n(rst_n),
        .en(ena & ui_in[0]),
        .aer_in_valid(ui_in[1]),
        .aer_in_addr(ui_in[2]),
        .aer_out_valid(aer_out_valid),
        .aer_out_addr(aer_out_addr)
    );

    // Saídas dedicadas:
    // uo_out[0]   = aer_out_valid
    // uo_out[2:1] = aer_out_addr[1:0]
    assign uo_out  = {5'b00000, aer_out_addr, aer_out_valid};

    // Pinos bidirecionais não utilizados (mantidos em alta impedância / zero)
    assign uio_out = 8'b00000000;
    assign uio_oe  = 8'b00000000;

    // Evita avisos de sinais não utilizados na síntese
    wire _unused = &{ui_in[7:3], uio_in, 1'b0};

endmodule