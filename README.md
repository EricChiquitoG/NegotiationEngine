[Digiprime](https://www.digiprime.eu/) is an EU project for the circular economy. This project is part of it and offers the ability to perform negotiations and contract signing between different parties.

This work is an addition to the work alread performed in [Negotiation Engine](https://github.com/EricChiquitoG/NegotiationEngine), which we have forked and added our additions. As this is used by the related [Digiprime](https://github.com/norlen/NegotiationEngine) project, our additions have mainly been to support the functionality required there. Some of these include retreiving a more complete set of information for both auctions and negotations and contract handling.

All our additions have been contained inside the `API PILOT 1` project. For a more complete view of the project, view the original README located at [Negotiation Engine](https://github.com/EricChiquitoG/NegotiationEngine)

## Getting started

Before getting started an environment variable that specifies the database address must be set. The easiest way is to create a `.env` file in the `API PILOT 1` folder containing

```bash
DATABASE_URL="mongodb://mongodb:27017/"
```

### Container

A dockerfile for the project exists under `API PILOT 1`, to run

```bash
docker build API\ PILOT\ 1 -t negotiation-engine    # build container
docker run -p 5000:5000 negotiation-engine          # run container
```

### Without container

It can also be started right away

```bash
cd API\ PILOT\ 1/
pip install
python app.py
```

### Other

To run a container that also has [Digiprime] and a database set up. A ready-made container exists at [Docker Hub](), see the README there for instructions. To build the container see [digiprime-container]().


## Usage

Original endpoints are documented in the original [Negotiation Engine]() project. Only our additions are documented below.

### Auth

Most of the endpoints accept basic authorization with only the username. This is inherited from the parent project, and as a final method for authorization has not been given we continued to use this.

### Auctions


#### List public auctions

`GET` request to `/rooms/public` returns a list of all available public auctions.

#### Example request

```bash
curl --request GET \
  --url http://localhost:5000/rooms/public \
  --header 'Authorization: Basic bm9ybGVuOg=='
```

<details>
<summary>Example response</summary>

```json
{
	"rooms": [
		{
			"_id": "62036fb8ca7196f92ae2d39c",
			"type": "auction",
			"privacy": "Public",
			"payload": {
				"name": {
					"val": [
						"Selling batteries"
					]
				},
				"created_by": {
					"val": [
						"norlen"
					]
				},
				"created_at": {
					"val": [
						"2022-02-09T07:39:36.494000Z"
					]
				},
				"auction_type": {
					"val": [
						"Ascending"
					]
				},
				"highest_bid": {
					"val": [
						null
					]
				},
				"highest_bidder": {
					"val": [
						""
					]
				},
				"closing_time": {
					"val": [
						"2022-02-24T00:39:00.000000Z"
					]
				},
				"sellersign": {
					"val": [
						"29f2a06bee0ef58efa052ceaf88f81eeab26e78207fefa5b34946d882c330189:b916efacee6a4e4ea958ebf79a05d03d"
					]
				},
				"buyersign": {
					"val": [
						""
					]
				},
				"templatetype": {
					"val": [
						"article"
					]
				},
				"room_name": {
					"val": [
						"Selling batteries"
					]
				},
				"reference_sector": {
					"val": [
						"Batteries"
					]
				},
				"reference_type": {
					"val": [
						"Product"
					]
				},
				"quantity": {
					"val": [
						"1000"
					]
				},
				"articleno": {
					"val": [
						"6202b296f597322ebac72f34"
					]
				}
			}
		}
  ]
}
```

</details>

#### Get auction info

`GET` request to `/rooms/<auctionId>/info` returns all information about a single auction.

##### Example request

```bash
curl --request GET \
  --url http://localhost:5000/rooms/61f1405adf8681687161315f/info \
  --header 'Authorization: Basic bm9ybGVuOg=='
```

<details>
<summary>Example response</summary>

```json
{
	"_id": "61f1405adf8681687161315f",
	"type": "auction",
	"privacy": null,
	"payload": {
		"name": {
			"val": [
				"My auction"
			]
		},
		"created_by": {
			"val": [
				"norlen"
			]
		},
		"created_at": {
			"val": [
				"2022-01-26 12:36:42.642000"
			]
		},
		"auction_type": {
			"val": [
				"Ascending"
			]
		},
		"highest_bid": {
			"val": [
				null
			]
		},
		"highest_bidder": {
			"val": [
				""
			]
		},
		"closing_time": {
			"val": [
				"2022-01-26 12:45:00"
			]
		},
		"sellersign": {
			"val": [
				"de66180cd5cc547e66bc4b5b5f71f3be48bca3e3db63292cd27ee53351413d20:a5c245dab60d46468d5f73151157c8e4"
			]
		},
		"buyersign": {
			"val": [
				""
			]
		},
		"templatetype": {
			"val": [
				null
			]
		},
		"room_name": {
			"val": [
				"My auction"
			]
		},
		"reference_sector": {
			"val": [
				"Composites"
			]
		},
		"reference_type": {
			"val": [
				"Material"
			]
		},
		"quantity": {
			"val": [
				"123"
			]
		},
		"articleno": {
			"val": [
				"61f14055dbe7522f80ada197"
			]
		}
	},
	"members": [
		{
			"_id": {
				"room_id": "61f1405adf8681687161315f",
				"username": "norlen"
			},
			"room_name": "My auction",
			"added_by": "norlen",
			"added_at": "2022-01-26 12:36:42.685000",
			"is_room_admin": true
		},
		{
			"_id": {
				"room_id": "61f1405adf8681687161315f",
				"username": "norlen1"
			},
			"room_name": "My auction",
			"added_by": "norlen",
			"added_at": "2022-01-26 12:36:42.763000",
			"is_room_admin": false
		}
	],
	"bids": [
		{
			"text": "5000",
			"sender": "norlen1",
			"created_at": "2022-01-26 12:37:06.495000",
			"distance": 277.4200024628344,
			"sign": "e7f8ae46a72e2bca1098d5df01e45a7ed2969ca965ac07bd02200fdca75f653f:0989548859f84d90895826c21495d5fb"
		}
	]
}
```

</details>


#### Get all auctions

`GET` request to `/room/all` returns a list of all auctions the user is participating in.

##### Example request

```bash
curl --request GET \
  --url http://localhost:5000/rooms/all \
  --header 'Authorization: Basic U2ViYXN0aWFuOg=='
```


<details>
<summary>Example response</summary>

```json
[
	{
		"_id": "6202b373a10ca517c592e275",
		"type": "auction",
		"privacy": "Private",
		"payload": {
			"name": {
				"val": [
					"Buy batteries #0"
				]
			},
			"created_by": {
				"val": [
					"norlen"
				]
			},
			"created_at": {
				"val": [
					"2022-02-08T18:16:19.944000Z"
				]
			},
			"auction_type": {
				"val": [
					"Descending"
				]
			},
			"highest_bid": {
				"val": [
					"100"
				]
			},
			"highest_bidder": {
				"val": [
					"Sebastian"
				]
			},
			"closing_time": {
				"val": [
					"2022-02-08T18:27:00.000000Z"
				]
			},
			"sellersign": {
				"val": [
					"29f2a06bee0ef58efa052ceaf88f81eeab26e78207fefa5b34946d882c330189:b916efacee6a4e4ea958ebf79a05d03d"
				]
			},
			"buyersign": {
				"val": [
					"b6b31762d313de53105810478cd5965bc34d444fe62b10d875eff11e1e853599:eb8631b00bb34a1899877022bdfceeb1"
				]
			},
			"templatetype": {
				"val": [
					"article"
				]
			},
			"room_name": {
				"val": [
					"Buy batteries #0"
				]
			},
			"reference_sector": {
				"val": [
					"Batteries"
				]
			},
			"reference_type": {
				"val": [
					"Product"
				]
			},
			"quantity": {
				"val": [
					"1000"
				]
			},
			"articleno": {
				"val": [
					"6202b2f6f597322ebac72f59,6202b335f597322ebac72f72"
				]
			}
		},
		"bids": [
			{
				"text": "100",
				"sender": "Sebastian",
				"created_at": "2022-02-08T18:16:28.409000Z",
				"distance": 796.1446685405374,
				"sign": "b6b31762d313de53105810478cd5965bc34d444fe62b10d875eff11e1e853599:eb8631b00bb34a1899877022bdfceeb1"
			}
		]
	}
]
```

</details>


#### name

##### Example request

```bash

```


<details>
<summary>Example response</summary>



</details>


### Negotiations

The API allows to create, list, get a single negotations. For a negotation you can bid, accept or reject.

The status field in the response can be one of

- `submitted`: no bids have been placed
- `offer`: the creator placed the last bid.
- `counter-offer`: the other party placed the last bid.
- `accepted`: if the negotiation has been accepted.
- `rejected`: if the negotiation has been rejected.

#### Create negotiation

`POST` request to `/negotiate` containing a form body to create a new negotiation.

##### Example request

```bash
curl --request POST \
  --url http://localhost:5000/negotiate \
  --header 'Authorization: Basic bm9ybGVuOg==' \
  --header 'Content-Type: multipart/form-data; boundary=---011000010111000001101001' \
  --form 'room_name=negotiation #1' \
  --form price=1000 \
  --form seller=Sebastian \
  --form reference_sector=Batteries \
  --form reference_type=Material \
  --form quantity=100 \
  --form articleno=620618063593f61446de42f6 \
  --form templatetype=article
```


<details>
<summary>Example response</summary>

```json
{
	"message": "The negotiation with id 6214de1683a1bdd717642654 has been created"
}
```

</details>


#### Get negotiation

`GET` request to `/negotiation/<negotiationId>/full` returns the complete information about a negotiation.

##### Example request

```bash
curl --request GET \
  --url http://localhost:5000/negotiate/6214dd9dc6800c95ee2c0d45 \
  --header 'Authorization: Basic bm9ybGVuOg=='
```


<details>
<summary>Example response</summary>

```json
{
	"_id": "6214dd9dc6800c95ee2c0d45",
	"name": "negotiation #1",
	"created_by": "norlen",
	"seller": "Sebastian",
	"created_at": "2022-02-22T12:57:01.147000Z",
	"end_date": "2022-02-25T06:40:07.154000Z",
	"current_offer": "1000",
	"offer_user": "norlen",
	"status": "rejected",
	"reference_sector": "Batteries",
	"reference_type": "Material",
	"quantity": "100",
	"articleno": "620618063593f61446de42f6"
}
```

</details>

<details>
<summary>Example response on accepted negotiation</summary>

```json
{
  "type": "contract",
  "contract": "",
}
```

</details>

#### List all negotiations

##### Example request

```bash
curl --request GET \
  --url http://localhost:5000/negotiate/list \
  --header 'Authorization: Basic bm9ybGVuOg=='
```


<details>
<summary>Example response</summary>

```json
[
	{
		"_id": "6214d8edc6800c95ee2c0d33",
		"name": "negotiation #1",
		"created_by": "norlen",
		"seller": "Sebastian",
		"created_at": "2022-02-22T12:37:01.900000Z",
		"end_date": "2022-02-22T12:50:37.573000Z",
		"current_offer": "1000",
		"offer_user": "Sebastian",
		"status": "accepted"
	},
]
```

</details>



#### Bid on negotiation

##### Example request

```bash
curl --request POST \
  --url http://localhost:5000/negotiate/6214d8edc6800c95ee2c0d33 \
  --header 'Authorization: Basic U2ViYXN0aWFuOg==' \
  --header 'Content-Type: multipart/form-data; boundary=---011000010111000001101001' \
  --form bid=1000
```


<details>
<summary>Example response</summary>

```json
{
	"message": "New offer submited for request with id 6214d8edc6800c95ee2c0d33"
}
```

</details>


#### Accept offer in negotiation

##### Example request

```bash
curl --request GET \
  --url http://localhost:5000/negotiate/6214d8edc6800c95ee2c0d33/accept \
  --header 'Authorization: Basic U2ViYXN0aWFuOg=='
```


<details>
<summary>Example response</summary>

```json
{
	"message": "The negotiation with id 6214d8edc6800c95ee2c0d33 has been accepted."
}
```

</details>



#### Reject offer in negotiation

##### Example request

```bash
curl --request GET \
  --url http://localhost:5000/negotiate/6214d8edc6800c95ee2c0d33/cancel \
  --header 'Authorization: Basic U2ViYXN0aWFuOg=='
```


<details>
<summary>Example response</summary>

```json
{
	"message": "The negotiation with id 6214d8edc6800c95ee2c0d33 has been rejected."
}
```

</details>

### Contracts

Support has been added for a more complete handling of contracts. With support for adding, getting, and listing.

Contract bodies can contain certain template parameters which will be substitued in during the signing process, these are specified by using `$key`.

#### Create contract

`POST` request to `contracts/create` with a JSON body containing

```json
{
  "title": "",
  "body": ""
}
```

to create a single contract.

##### Example request

```bash
curl --request POST \
  --url http://localhost:5000/contracts/create \
  --header 'Content-Type: application/json' \
  --data '{
	"title": "article",
	"body": "details"
}'
```


<details>
<summary>Example response</summary>

```json
{
	"id": "6214ea9ad6db7bca66de2c3a",
	"message": "successfully created contract"
}
```

</details>


#### Get contract

`GET` request to `contracts/<contractId>` to get information about a single contract.

##### Example request

```bash
curl --request GET \
  --url http://localhost:5000/contracts/6214ea9ad6db7bca66de2c3a
```


<details>
<summary>Example response</summary>

```json
{
	"_id": "6214ea9ad6db7bca66de2c3a",
	"title": "article",
	"body": "details"
}
```

</details>


#### List contracts

`GET` request to `contracts/list` to list all the available contracts.

##### Example request

```bash
curl --request GET \
  --url http://localhost:5000/contracts/list
```


<details>
<summary>Example response</summary>

```json
[
	{
		"_id": "6214ea9ad6db7bca66de2c3a",
		"title": "article",
		"body": "details"
	}
]
```

</details>
