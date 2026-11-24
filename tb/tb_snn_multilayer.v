`timescale 1ns / 1ps

module tb_snn_multilayer;

    reg        clk;
    reg        rst_n;
    reg        en;
    reg  [1:0] spikes_in;
    wire [3:0] hidden_spikes;
    wire [3:0] spikes_out;

    snn_multilayer #(
        .WIDTH(8),
        .V_TH(100)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .spikes_in(spikes_in),
        .hidden_spikes(hidden_spikes),
        .spikes_out(spikes_out)
    );

    always #5 clk = ~clk;

    integer i;
    initial begin
        $dumpfile("build/snn_multilayer.vcd");
        $dumpvars(0, tb_snn_multilayer);

        clk = 0; rst_n = 0; en = 0; spikes_in = 2'b00;

        #20 rst_n = 1;
        en = 1;

        // Injeta pulsos contínuos por 60 ciclos para propagar pelas duas camadas
        for (i = 0; i < 60; i = i + 1) begin
            @(posedge clk);
            spikes_in[0] = (i % 2 == 0);
            spikes_in[1] = (i % 3 == 0);
        end

        @(posedge clk);
        spikes_in = 2'b00;
        repeat (10) @(posedge clk);

        $finish;
    end

    always @(posedge clk) begin
        if (|hidden_spikes || |spikes_out)
            $display("t=%0t | L1(oculta)=%b | L2(saida)=%b", $time, hidden_spikes, spikes_out);
    end

endmodule