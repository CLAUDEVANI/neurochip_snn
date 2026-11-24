`timescale 1ns / 1ps

module tb_tt_um_neurochip_snn;

    reg        clk;
    reg        rst_n;
    reg        ena;
    reg  [7:0] ui_in;
    reg  [7:0] uio_in;
    wire [7:0] uo_out;
    wire [7:0] uio_out;
    wire [7:0] uio_oe;

    tt_um_neurochip_snn u_dut (
        .ui_in(ui_in),
        .uo_out(uo_out),
        .uio_in(uio_in),
        .uio_out(uio_out),
        .uio_oe(uio_oe),
        .ena(ena),
        .clk(clk),
        .rst_n(rst_n)
    );

    initial clk = 0;
    always #10 clk = ~clk; // 50 MHz

    integer i;
    integer spikes_seen;

    initial begin
        rst_n       = 0;
        ena         = 0;
        ui_in       = 8'h00;
        uio_in      = 8'h00;
        spikes_seen = 0;

        #25;
        if (uio_oe !== 8'h00 || uio_out !== 8'h00) begin
            $display("ERRO: uio_oe/uio_out devem ser 0!");
            $fatal(1);
        end
        if (uo_out !== 8'h00) begin
            $display("ERRO: uo_out deveria estar zerado no reset (got %02h)", uo_out);
            $fatal(1);
        end

        // Libera reset, mas mantém ena=0 (core_en deve continuar 0)
        rst_n = 1;
        ui_in = 8'b0000_0011; // en=1, aer_in_valid=1, addr=0
        @(posedge clk); #1;
        if (uo_out[7] !== 1'b0) begin
            $display("ERRO: core_en deveria ser 0 quando ena=0");
            $fatal(1);
        end

        // Habilita o chip (ena=1) e envia rajada de eventos AER alternando canais 0 e 1
        ena = 1;
        for (i = 0; i < 40; i = i + 1) begin
            @(negedge clk);
            ui_in = {5'b00000, i[0], 1'b1, 1'b1}; // addr=i[0], valid=1, en=1
            #1;
            if (uo_out[0] === 1'b1) begin
                spikes_seen = spikes_seen + 1;
            end
            @(posedge clk); #1;
            if (uo_out[7] !== 1'b1) begin
                $display("ERRO: core_en deveria ser 1 quando ena=1 e ui_in[0]=1");
                $fatal(1);
            end
        end

        if (spikes_seen == 0) begin
            $display("ERRO: Nenhum spike AER observado na saida do Tiny Tapeout!");
            $fatal(1);
        end

        // Confirma telemetria (spike_cnt modulo 16)
        if (uo_out[6:3] !== spikes_seen[3:0]) begin
            $display("ERRO: spike_cnt (%0d) diverge de spikes_seen mod 16 (%0d)",
                     uo_out[6:3], spikes_seen[3:0]);
            $fatal(1);
        end

        $display("PASS: Wrapper Tiny Tapeout validado! (spikes_seen=%0d, spike_cnt=%0d)",
                 spikes_seen, uo_out[6:3]);
        $finish;
    end

endmodule
