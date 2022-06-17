// 2-bit multiplier

module mult_2_bit (
    input  logic [1:0]  a,
    output logic [3:0]  o,
    input  logic [1:0]  b
);

  logic and01;
  logic and10;
  logic and11;
  logic and0110;

  assign and01 = a[0] & b[1];
  assign and10 = a[1] & b[0];
  assign and11 = a[1] & b[1];
  assign and0110 = and01 & and10;

  assign o[0] = a[0] & b[0];
  assign o[1] = and01 ^ and10;
  assign o[2] = and11 ^ and0110;
  assign o[3] = and11 & and0110;

endmodule