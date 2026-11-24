`timescale 1ns / 1ps

module aer_top (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    // Entrada AER
    input  wire       aer_in_valid,
    input  wire       aer_in_addr,
    // Saída AER com fila de eventos pendentes
    output reg        aer_out_valid,
    output reg  [1:0] aer_out_addr
);

    wire [1:0] spikes_in;
    wire [3:0] spikes_out;

    reg  [3:0] pending_spikes;
    reg  [3:0] served_mask;

    // Decodificador AER de entrada
    assign spikes_in[0] = aer_in_valid & (~aer_in_addr);
    assign spikes_in[1] = aer_in_valid & ( aer_in_addr);

    // Camada neuromórfica (4 neurônios, 8 sinapses STDP)
    snn_layer #(
        .WIDTH(8),
        .V_TH(100)
    ) u_layer (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .spikes_in(spikes_in),
        .spikes_out(spikes_out)
    );

    // Árbitro de saída: seleciona 1 evento pendente por ciclo
    always @(*) begin
        served_mask   = 4'b0000;
        aer_out_valid = 1'b0;
        aer_out_addr  = 2'd0;

        if (pending_spikes[0]) begin
            aer_out_valid = 1'b1;
            aer_out_addr  = 2'd0;
            served_mask   = 4'b0001;
        end else if (pending_spikes[1]) begin
            aer_out_valid = 1'b1;
            aer_out_addr  = 2'd1;
            served_mask   = 4'b0010;
        end else if (pending_spikes[2]) begin
            aer_out_valid = 1'b1;
            aer_out_addr  = 2'd2;
            served_mask   = 4'b0100;
        end else if (pending_spikes[3]) begin
            aer_out_valid = 1'b1;
            aer_out_addr  = 2'd3;
            served_mask   = 4'b1000;
        end
    end

    // Fila de eventos: limpa o evento servido e acumula novos disparos
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pending_spikes <= 4'b0000;
        end else if (en) begin
            pending_spikes <= (pending_spikes & ~served_mask) | spikes_out;
        end
    end

endmodule