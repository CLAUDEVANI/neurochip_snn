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

    wire       core_en;
    wire       aer_out_valid;
    wire [1:0] aer_out_addr;
    reg  [3:0] spike_cnt;

    assign core_en = ena & ui_in[0];

    // Mapeamento dos pinos do Tiny Tapeout:
    // ui_in[0]    = en (enable do núcleo)
    // ui_in[1]    = aer_in_valid
    // ui_in[2]    = aer_in_addr
    // uo_out[0]   = aer_out_valid
    // uo_out[2:1] = aer_out_addr[1:0]
    // uo_out[6:3] = spike_cnt[3:0] (telemetria de disparos AER)
    // uo_out[7]   = core_en (status de operação do núcleo)
    aer_top u_core (
        .clk(clk),
        .rst_n(rst_n),
        .en(core_en),
        .aer_in_valid(ui_in[1]),
        .aer_in_addr(ui_in[2]),
        .aer_out_valid(aer_out_valid),
        .aer_out_addr(aer_out_addr)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spike_cnt <= 4'd0;
        end else if (core_en && aer_out_valid) begin
            spike_cnt <= spike_cnt + 4'd1;
        end
    end

    assign uo_out  = {core_en, spike_cnt, aer_out_addr, aer_out_valid};

    // Pinos bidirecionais mantidos em entrada / alta impedância
    assign uio_out = 8'b00000000;
    assign uio_oe  = 8'b00000000;

    // Evita avisos de sinais não utilizados na síntese
    wire _unused = &{ui_in[7:3], uio_in, 1'b0};

endmodule
