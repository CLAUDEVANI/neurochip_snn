`timescale 1ns / 1ps

module tb_aer_real_signal;

    reg        clk;
    reg        rst_n;
    reg        en;
    reg        aer_in_valid;
    reg        aer_in_addr;
    wire       aer_out_valid;
    wire [1:0] aer_out_addr;

    reg [1:0] stimuli [0:199];
    integer i;

    aer_top dut (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .aer_in_valid(aer_in_valid),
        .aer_in_addr(aer_in_addr),
        .aer_out_valid(aer_out_valid),
        .aer_out_addr(aer_out_addr)
    );

    always #5 clk = ~clk;

    initial begin
        $readmemh("build/aer_stimuli.hex", stimuli);
        $dumpfile("build/aer_real_signal.vcd");
        $dumpvars(0, tb_aer_real_signal);

        clk = 0; rst_n = 0; en = 0;
        aer_in_valid = 0; aer_in_addr = 0;

        #20 rst_n = 1;
        en = 1;

        for (i = 0; i < 200; i = i + 1) begin
            @(posedge clk);
            aer_in_valid = stimuli[i][1];
            aer_in_addr  = stimuli[i][0];
        end

        @(posedge clk);
        aer_in_valid = 1'b0;
        repeat (10) @(posedge clk);

        $finish;
    end

    always @(posedge clk) begin
        if (aer_out_valid)
            $display("ciclo=%3d | t=%0t | SPIKE AER OUT -> Neuronio %0d", i, $time, aer_out_addr);
    end

endmodule