`timescale 1ns / 1ps

module stdp_synapse #(
    parameter WIDTH   = 8,
    parameter INIT_W  = 35,
    parameter MAX_W   = 127,
    parameter WINDOW  = 5,
    parameter LTP     = 3,
    parameter LTD     = 2
)(
    input  wire             clk,
    input  wire             rst_n,
    input  wire             en,
    input  wire             pre_spike,
    input  wire             post_spike,
    output reg  [WIDTH-1:0] weight,
    output wire [WIDTH-1:0] syn_out
);

    reg [3:0] pre_trace;
    reg [3:0] post_trace;

    // Só entrega o peso ao neurônio quando há pulso de entrada
    assign syn_out = pre_spike ? weight : {WIDTH{1'b0}};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            weight     <= INIT_W[WIDTH-1:0];
            pre_trace  <= 4'd0;
            post_trace <= 4'd0;
        end else if (en) begin
            // 1. Atualiza traço pré-sináptico
            if (pre_spike)
                pre_trace <= WINDOW[3:0];
            else if (pre_trace > 4'd0)
                pre_trace <= pre_trace - 4'd1;

            // 2. Atualiza traço pós-sináptico
            if (post_spike)
                post_trace <= WINDOW[3:0];
            else if (post_trace > 4'd0)
                post_trace <= post_trace - 4'd1;

            // 3. Regra STDP (LTP tem prioridade se coincidirem)
            if (post_spike && (pre_trace > 4'd0)) begin
                if (weight + LTP > MAX_W)
                    weight <= MAX_W[WIDTH-1:0];
                else
                    weight <= weight + LTP[WIDTH-1:0];
            end else if (pre_spike && (post_trace > 4'd0)) begin
                if (weight < LTD)
                    weight <= {WIDTH{1'b0}};
                else
                    weight <= weight - LTD[WIDTH-1:0];
            end
        end
    end

endmodule