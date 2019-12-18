#!/usr/bin/env ruby
require 'factory_bot'
require 'faker'
require 'active_support/all'
require 'csv'

@registry_volume=40

class FakeN26
    attr_accessor :date,
                                :payee,
                                :account_number,
                                :transaction_type,
                                :payment_reference,
                                :category,
                                :amount_eur,
                                :amount_foreign_currency,
                                :type_foreign_currency,
                                :exchange_rate
end

FactoryBot.define do
  factory :fake_N26 do
    date { Faker::Date.in_date_period(year:2019, month:12) }
    payee { Faker::Company.bs }
    account_number { Faker::Bank.iban(country_code: 'DE') }
    transaction_type { 'MasterCard Payment' }
    payment_reference { Faker::Commerce.product_name }
    category { ['Outgoing Transfer', 'Bars & Restaurants', 'Direct Debit', 'Transport & Car'].sample }
        amount_eur { Faker::Commerce.price(range: -600.0..600.0, as_string: true) }
        amount_foreign_currency { amount_eur }
        type_foreign_currency { 'EUR' }
        exchange_rate { '1.0' }
  end
end

FactoryBot.build_list(:fake_N26, @registry_volume).map { |data|
  puts data.instance_values.map { |key, val|  "\"#{val}\"" }.join(',')
}
